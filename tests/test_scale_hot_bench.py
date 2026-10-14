"""tests/test_scale_hot_bench.py — EXPANSION_5K E0.1: humo rápido de scripts/bench_scale.py con el catálogo REAL.

El banco de 5.000 empresas (tests/test_scale_budget.py) solo corre con KH_SCALE=1; esto vigila en la suite normal que
el banco siga funcionando (si una vista cambia de firma, se nota aquí y no la noche de la medición) y que no escriba
nada: sin base, sin tocar data/, un objeto JSON con las claves que usa el presupuesto.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_banco_con_el_catalogo_real_da_el_json_del_presupuesto(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != 'DATABASE_URL'}
    env['KHIPU_SCHEDULER'] = 'off'
    data_dir = os.path.join(ROOT, 'data')
    before = {f: os.path.getmtime(os.path.join(data_dir, f)) for f in os.listdir(data_dir)}
    out = tmp_path / 'b.json'
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'bench_scale.py'), '--n', '0', '--samples', '20',
                        '--out', str(out)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    R = json.loads(r.stdout)
    assert json.loads(out.read_text(encoding='utf-8')) == R
    assert R['graph'] == 'snapshot' and R['n_ids'] >= 937 and R['reader_nodes'] >= 900 and not R['errors']
    for k in ('graph_core', 'impact', 'card_build', 'structure', 'first_card_total', 'nrs_all', 'rho', 'pagerank'):
        assert isinstance(R['ms'].get(k), (int, float)), k
    for k in ('card', 'impact_payload', 'scenario', 'search', 'detect'):
        assert R['p'][k]['p50'] >= 0, k
    assert R['rss_mb']['peak'] and R['bytes']['factors'] > 0 and R['bytes']['metrics'] > 0
    assert abs(R['rho'] - 1.210718) < 1e-4
    assert {f: os.path.getmtime(os.path.join(data_dir, f)) for f in os.listdir(data_dir)} == before
    # --out en data/ se rechaza
    bad = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'bench_scale.py'), '--n', '0',
                          '--out', os.path.join(data_dir, 'x.json')], cwd=ROOT, env=env, capture_output=True,
                         text=True, timeout=60)
    assert bad.returncode != 0 and not os.path.exists(os.path.join(data_dir, 'x.json'))
