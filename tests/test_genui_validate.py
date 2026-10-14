"""tests/test_genui_validate.py — el VALIDADOR COMPILADO de kblocks/1 (core/genui/validate.py, solo biblioteca estándar)
contra el ORÁCULO jsonschema (requirements-dev.txt), como core/gates frente a pySHACL (docs/CHAT_UI_GENERATIVA.md
§10.1, F1 paso 6).

  (a) siempre: los ejemplos válidos pasan y los inválidos fallan también con el validador compilado; la fecha-hora
      RFC 3339 es la misma regla que la prueba del esquema; los ids CANÓNICOS reales del grafo (mayúsculas, espacios,
      «&») y las generaciones de las vistas rápidas (texto) cumplen el contrato; un sobre real valida en < 2 ms.
  (b) con jsonschema: ≥ 1.000 mutaciones aleatorias (semilla fija) de sobres y planes → 0 diferencias.
"""
import copy
import json
import os
import random
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))

from core.genui import schema as S  # noqa: E402
from core.genui import validate as V  # noqa: E402

EX = json.load(open(os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'examples.kblocks.json'), encoding='utf-8'))
GOLDEN = os.path.join(ROOT, 'tests', 'golden', 'impl_genui.build@1.json')
IN_CI = (os.getenv('CI') or os.getenv('GITHUB_ACTIONS') or '').lower() in ('1', 'true', 'yes')

try:
    import jsonschema  # noqa: F401
    HAVE = True
except ImportError:
    HAVE = False


def _real_envelopes():
    with open(GOLDEN, encoding='utf-8') as fh:
        doc = json.load(fh)
    return [e for c in doc['cases'] for e in c['output']]


# ── (a) siempre ─────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize('case', EX['valid'], ids=[c['name'] for c in EX['valid']])
def test_validos_pasan_compilado(case):
    assert V.errors(case['envelope']) == []


@pytest.mark.parametrize('case', EX['invalid'], ids=[c['why'] for c in EX['invalid']])
def test_invalidos_fallan_compilado(case):
    assert V.errors(case['envelope']), case['why']


def test_planes_compilado():
    for p in EX['plans_valid']:
        assert V.is_valid(p, 'Plan')
    for c in EX['plans_invalid']:
        assert not V.is_valid(c['plan'], 'Plan'), c['why']


def test_fecha_hora_rfc3339():
    for ok in ('2026-10-13T15:02:11Z', '2026-10-13T15:02:11.250Z', '2026-10-13T10:02:11-05:00'):
        assert V.is_datetime(ok)
    for bad in ('2026-10-13', '13/10/2026 15:02', '2026-02-30T10:00:00Z', '2026-10-13T15:02Z'):
        assert not V.is_datetime(bad), bad


def test_ids_canonicos_y_generacion_reales():
    """kblocks/1 corregido en F1: los ids del grafo son CANÓNICOS («Nvidia», «Boyd Thermal», «Cushman & Wakefield»),
    no minúsculas; la generación de una vista rápida es un texto («g0.r1d6ee563.c03225529.snapshot»)."""
    with open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8') as fh:
        ids = [n['id'] for n in json.load(fh)['nodes']]
    bad = [i for i in ids if not V.is_valid({'id': i, 'label': i[:80]}, 'Entity')]
    assert not bad, bad[:10]
    assert V.is_valid('g0.r1d6ee563.c03225529.snapshot', 'Generation') and V.is_valid(51, 'Generation')
    assert not V.is_valid('<script>', 'Generation') and not V.is_valid(-1, 'Generation')
    assert not V.is_valid({'id': '<b>x</b>', 'label': 'x'}, 'Entity')


def test_sobres_reales_validan_rapido():
    envs = _real_envelopes()
    assert envs
    for e in envs:
        assert V.errors(e) == []
    t0 = time.perf_counter()
    for _ in range(50):
        for e in envs:
            V.is_valid(e)
    per = (time.perf_counter() - t0) * 1000 / (50 * len(envs))
    assert per < 2.0, f'{per:.2f} ms por sobre'


def test_catalogo_del_esquema():
    assert len(S.block_types()) == 17
    assert 'place_order' not in S.action_kinds()


# ── (b) conformidad con el oráculo ───────────────────────────────────────────────────────────────────────────────
def test_guardia_ci_exige_jsonschema():
    if IN_CI:
        assert HAVE


def _oracle(def_name):
    from jsonschema import Draft202012Validator, FormatChecker
    fc = FormatChecker()

    @fc.checks('date-time', raises=ValueError)
    def _dt(value):
        if isinstance(value, str) and not V.is_datetime(value):
            raise ValueError('no es RFC 3339 con hora y zona')
        return True
    sch = dict(S.load())
    sch['$ref'] = '#/$defs/' + def_name
    return Draft202012Validator(sch, format_checker=fc)


_STRS = ('', 'x', 'kblocks/2', 'tool', 'view', 'pct', 'USD', 'CCY', 'ready', 'error', 'planned', 'final', 'partial',
         'auto', 'plan', 'es', 'en', 'F1', 'F1234', 'hot_kernel', 'client_js', 'supplier', 'center', 'fab', 'partner',
         '2026-10-13', '2026-10-13T15:02:11Z', '2026-02-30T00:00:00Z', 'not a date', 'https://evil.example/x.png',
         '/static/genui/chip.svg', '/static/genui/../x.svg', 'open_window', 'place_order', 'broker', 'geo', 'world',
         'pros_cons', 'disclaimer', 'system', 'tool', 'model', 'Nvidia', 'Boyd Thermal', '<img onerror=x>', 'a' * 90,
         'a' * 450, 'g0.r1.snapshot', 'chart.line', 'text', 'metric.tiles', 'sources', 'unknown.type', '1Y', 'YTD')
_VALS = (None, True, False, 0, 1, -1, 1.5, 101, 1e9, 0.5, [], {}, [1, 2], {'es': 'a', 'en': 'b'}, {'es': 'solo'},
         {'id': 'Nvidia', 'label': 'Nvidia'}) + _STRS


def _small(env):
    """Un sobre real más liviano para mutar (el oráculo es lento con series largas): mismas formas, menos ítems."""
    e = copy.deepcopy(env)
    for b in e['blocks']:
        d = b.get('data') or {}
        for s in d.get('series') or []:
            s['points'] = s['points'][:6]
        if isinstance(d.get('spark'), dict):
            d['spark']['points'] = d['spark']['points'][:4]
        for k in ('nodes', 'edges', 'hops', 'items', 'top_suppliers', 'top_customers', 'marks'):
            if isinstance(d.get(k), list):
                d[k] = d[k][:4]
        if b['type'] == 'graph.mini':
            keep = {n['entity']['id'] for n in d['nodes']}
            d['edges'] = [x for x in env['blocks'][e['blocks'].index(b)]['data']['edges']
                          if x['s'] in keep and x['t'] in keep][:4]
    return e


def _paths(x, path=()):
    out = [path]
    if isinstance(x, dict):
        for k, v in x.items():
            out.extend(_paths(v, path + (k,)))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            out.extend(_paths(v, path + (i,)))
    return out


def _get(x, path):
    for p in path:
        x = x[p]
    return x


def _mutate(doc, rng):
    d = copy.deepcopy(doc)
    paths = _paths(d)
    for _ in range(rng.choice((1, 1, 1, 2, 3))):
        paths = _paths(d)
        p = rng.choice(paths)
        op = rng.random()
        if not p:
            continue
        parent, key = _get(d, p[:-1]), p[-1]
        cur = parent[key]
        if op < 0.30:                                   # cambiar el valor
            parent[key] = copy.deepcopy(rng.choice(_VALS))
        elif op < 0.45 and isinstance(parent, dict):    # quitar la clave
            del parent[key]
        elif op < 0.55 and isinstance(parent, dict):    # clave desconocida al lado
            parent[rng.choice(('onclick', 'html', 'extra', 'v', 'type', 'unit', 'as_of', 'src'))] = \
                copy.deepcopy(rng.choice(_VALS))
        elif op < 0.65 and isinstance(cur, list):       # duplicar o vaciar una lista
            if cur and rng.random() < 0.6:
                cur.extend(copy.deepcopy(cur[:rng.randint(1, 20)]))
            else:
                cur.clear()
        elif op < 0.75 and isinstance(cur, (int, float)) and not isinstance(cur, bool):
            parent[key] = rng.choice((cur * -1, cur + 1000, cur / 3, int(cur), float(cur), -0.0001))
        elif op < 0.85 and isinstance(cur, str):
            parent[key] = rng.choice((cur.upper(), cur + ' ', '', cur * 30, cur[:-1] if cur else 'x', cur + '\n'))
        elif isinstance(parent, list) and len(parent) > 1:   # mover un ítem
            parent.insert(rng.randrange(len(parent)), parent.pop(key))
        else:
            parent[key] = copy.deepcopy(rng.choice(_VALS))
    return d


@pytest.mark.skipif(not HAVE, reason='jsonschema no instalado (requirements-dev.txt)')
def test_conformidad_con_jsonschema_1000_mutaciones():
    """≥ 1.000 mutaciones con semilla fija: 850 de BLOQUES sueltos (contra $defs/Block: el oráculo tarda ~50 ms por
    sobre entero, así la prueba dura segundos), 200 de sobres enteros y 250 de planes de la IA → 0 diferencias."""
    rng = random.Random(20261013)
    env_or, blk_or, plan_or = _oracle('Envelope'), _oracle('Block'), _oracle('Plan')
    bases = [c['envelope'] for c in EX['valid']] + [_small(e) for e in _real_envelopes()]
    blocks = [b for e in bases for b in e['blocks']] + [b for c in EX['invalid'] for b in c['envelope']['blocks']]
    plans = list(EX['plans_valid']) + [c['plan'] for c in EX['plans_invalid']]
    n, diffs, n_valid = 0, [], 0
    for i in range(850):
        m = _mutate(blocks[i % len(blocks)], rng)
        a, b = V.is_valid(m, 'Block'), blk_or.is_valid(m)
        n += 1
        n_valid += a
        if a != b:
            diffs.append(('block', i, a, b, [list(e.absolute_path) for e in blk_or.iter_errors(m)][:2], V.errors(m, 'Block')))
    for i in range(200):
        m = _mutate(bases[i % len(bases)], rng)
        a, b = V.is_valid(m), env_or.is_valid(m)
        n += 1
        if a != b:
            diffs.append(('env', i, a, b, V.errors(m)))
    for i in range(250):
        m = _mutate(plans[i % len(plans)], rng)
        a, b = V.is_valid(m, 'Plan'), plan_or.is_valid(m)
        n += 1
        if a != b:
            diffs.append(('plan', i, a, b))
    for c in EX['invalid']:                             # los inválidos del contrato, sin mutar
        n += 1
        if V.is_valid(c['envelope']) != env_or.is_valid(c['envelope']):
            diffs.append(('inv', c['why']))
    assert n >= 1000
    assert 0 < n_valid < 850, n_valid                   # la muestra tiene válidos e inválidos (si no, no prueba nada)
    assert not diffs, diffs[:5]
