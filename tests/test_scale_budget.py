"""tests/test_scale_budget.py — EXPANSION_5K E0.1: presupuesto de ESCALA a 5.000 empresas (lento: solo con KH_SCALE=1).

Corre scripts/bench_scale.py en un proceso aparte (memoria limpia, sin base) sobre el grafo sintético de 5.000 empresas
(scripts/gen_synth_graph.py) y exige que lo que la tabla 1 del plan (docs/expansion/EXPANSION_5K.md §1) ya cumple NO
empeore más de un 20 %:
  · metas de la tabla 1 ya alcanzadas → medido ≤ meta × 1,2;
  · "lo que ya está bien a 5k" → medido ≤ referencia medida en el plan × 1,2 (sub-milisegundo: + 0,15 ms de ruido
    medido entre corridas).
Las metas que todavía NO se cumplen (PENDING) solo se informan. Además: los lectores ven el grafo sintético entero y
ρ es el del catálogo real (el levantamiento lo conserva: el kernel no cambió ningún número).

    KH_SCALE=1 pytest tests/test_scale_budget.py -q -s       (≈ 10-20 s)
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

pytestmark = pytest.mark.skipif(
    os.getenv('KH_SCALE') != '1',
    reason='prueba de escala lenta (grafo sintético de 5.000 empresas): correr con KH_SCALE=1')

N = 5000
RHO_REAL = 1.210718          # ρ del catálogo real (kernel.params vigente); el levantamiento lo conserva
SUBMS_SLACK = 0.15           # ms: ruido medido en tiempos de menos de 1 ms (escenario p50 0,17-0,35 ms en 6 corridas)

# (ruta en el JSON del banco, meta de la tabla 1 a 5k, unidad, etiqueta)
TABLE1_MET = [
    (('ms', 'impact'), 150.0, 'ms', 'Construir Impact (todos los choques) — E1.1'),
    (('ms', 'first_card_total'), 500.0, 'ms', 'Primera /api/hot/card tras una escritura — E1.2'),
    (('p', 'card', 'p50'), 1.0, 'ms', 'Ficha p50 — E1.2'),
    (('rss_mb', 'peak'), 350.0, 'MB', 'Pico de memoria del proceso — E1.2 + E1.3'),
    (('p', 'search', 'p50'), 20.0, 'ms', 'MCP search_companies p50 — E1.5'),
    # cumplida tras la revisión del lote J (sin el costo de importar core.world, Ψ de flujo sin ordenar): 96-141 ms
    (('ms', 'structure'), 150.0, 'ms', 'Modelo de estructura (tensor) — E1.2'),
]
# metas que todavía no se cumplen: solo se informan (hoy ninguna de la tabla 1 del servidor)
TABLE1_PENDING = []
# "Lo que ya está bien a 5k" (fila final de la tabla 1): referencia medida en el plan
ALREADY_GOOD = [
    (('p', 'impact_payload', 'p50'), 0.014, 'ms', 'impacto precalculado'),
    (('p', 'scenario', 'p50'), 0.2, 'ms', 'escenario'),
    (('ms', 'nrs_all'), 159.0, 'ms', 'NRS de todas'),
    (('ms', 'rho'), 14.0, 'ms', 'ρ'),
    (('ms', 'pagerank'), 7.0, 'ms', 'PageRank'),
    (('p', 'detect', 'p50'), 0.34, 'ms', 'detector de contexto'),
]


def _get(R, path):
    v = R
    for k in path:
        v = (v or {}).get(k) if isinstance(v, dict) else None
    return v


@pytest.fixture(scope='module')
def bench():
    env = {k: v for k, v in os.environ.items() if k != 'DATABASE_URL'}
    env['KHIPU_SCHEDULER'] = 'off'
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'bench_scale.py'), '--n', str(N),
                        '--repeat', '3'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stderr[-2000:]
    R = json.loads(r.stdout)
    print('\n[bench_scale 5k] ' + json.dumps({k: R.get(k) for k in ('ms', 'p', 'rss_mb', 'bytes')}, default=str))
    return R


def test_el_banco_mide_el_grafo_sintetico_entero(bench):
    R = bench
    assert R['graph'] == 'synthetic' and R['n_ids'] >= N and R['reader_nodes'] == N
    assert R['nrs_n'] == N and not R['errors'], R['errors']
    assert abs(R['rho'] - RHO_REAL) < 1e-4, R['rho']            # mismos números del kernel


@pytest.mark.parametrize('path, target, unit, label', TABLE1_MET, ids=[x[3] for x in TABLE1_MET])
def test_meta_de_la_tabla_1_no_empeora(bench, path, target, unit, label):
    v = _get(bench, path)
    assert v is not None, f'{label}: el banco no lo midió'
    assert v <= target * 1.2, f'{label}: {v} {unit} > meta {target} {unit} + 20 %'


@pytest.mark.parametrize('path, ref, unit, label', ALREADY_GOOD, ids=[x[3] for x in ALREADY_GOOD])
def test_lo_que_ya_estaba_bien_no_empeora(bench, path, ref, unit, label):
    v = _get(bench, path)
    assert v is not None, f'{label}: el banco no lo midió'
    allowed = ref * 1.2 + (SUBMS_SLACK if ref < 1.0 else 0.0)
    assert v <= allowed, f'{label}: {v} {unit} > referencia {ref} {unit} + 20 %'


def test_metas_pendientes_solo_se_informan(bench):
    rows = []
    for path, target, unit, label in TABLE1_PENDING:
        v = _get(bench, path)
        rows.append(f"{label}: {v} {unit} (meta {target}) {'OK' if v is not None and v <= target else 'PENDIENTE'}")
    print('\n' + '\n'.join(rows))
