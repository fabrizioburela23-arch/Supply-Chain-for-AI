"""tests/test_scenario_pnl.py — escenario → DINERO (BRECHAS L2-13 / PROP-16; batch I3). Sin red (todo con datos fijos).

  · medición: caída relativa al mercado en la ventana; series inservibles (sin datos, sin ajustar, congeladas,
    corruptas) se descartan con su razón, nunca se corrigen;
  · ajuste con efecto fijo por episodio: recupera un κ conocido; con ruido puro da `weak` y razones;
  · traducción: −κ·Σ usd·impacto ± banda; débil / sin calibrar / otro motor / sin posiciones → SIN cifra;
  · el artefacto kernel.calibration@1.0.0 se reproduce byte a byte desde su archivo de entradas (hash) y HOY dice
    `weak` (la app no da cifra); el script de calibración corre de punta a punta con precios falsos (sin red);
  · POST /api/hot/scenario_pnl (servidor real, snapshot sin base) y la ficha whatif citan la versión de κ.
"""
import json
import math
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))


# ── medición ─────────────────────────────────────────────────────────────────
def test_caida_relativa_al_mercado():
    from core import scenario_pnl as SP
    m = {'2022-10-06': 100.0, '2022-10-13': 95.0, '2022-10-20': 90.0, '2022-10-27': 100.0}
    i = {'2022-10-06': 50.0, '2022-10-13': 40.0, '2022-10-20': 45.0, '2022-10-27': 52.0}
    # base = cierre ≤ t0 (10-06); peor relativo = 40/50 / (95/100) − 1 = −0.157894…
    assert SP.relative_drawdown(i, m, '2022-10-06', '2022-10-27') == pytest.approx(0.8 / 0.95 - 1)
    up = {'2022-10-06': 50.0, '2022-10-13': 60.0}
    assert SP.relative_drawdown(up, m, '2022-10-06', '2022-10-13') == 0.0          # nunca cayó: 0, no positivo
    assert SP.relative_drawdown({'2022-10-13': 1.0}, m, '2022-10-06', '2022-10-27') is None   # sin base


def test_series_inservibles_se_descartan_con_su_razon():
    from core import scenario_pnl as SP
    t0, t1 = '2022-10-06', '2022-10-27'
    good = {'closes': {'2022-09-30': 10.0, '2022-10-07': 9.0, '2022-10-14': 9.5}}
    assert SP.series_problem(good, t0, t1) is None
    assert SP.series_problem({'closes': {}}, t0, t1) == 'no_data'
    assert SP.series_problem(dict(good, adjusted=False), t0, t1) == 'unadjusted'
    assert SP.series_problem({'closes': {'2022-09-30': 40.6, '2022-10-07': 40.6, '2022-10-14': 40.6}}, t0, t1) == 'frozen'
    # el caso real de SSNLF (OTC): un "cierre" de 4,8e15 y luego 40,6
    assert SP.series_problem({'closes': {'2022-09-30': 4.8e15, '2022-10-07': 40.6, '2022-10-14': 41.0}}, t0, t1) \
        == 'corrupt'


# ── ajuste ───────────────────────────────────────────────────────────────────
def _synthetic(kappa, noise, n_per=20, eps=('e1', 'e2', 'e3'), seed=1):
    rng = random.Random(seed)
    pts = []
    for k, e in enumerate(eps):
        a = -0.05 * (k + 1)
        for j in range(n_per):
            imp = rng.uniform(0.0, 0.8)
            pts.append({'episode': e, 'id': f'{e}-{j}', 'impact': imp, 'y': a - kappa * imp + rng.gauss(0, noise)})
    return pts


def test_ajuste_recupera_un_kappa_conocido():
    from core import scenario_pnl as SP
    f = SP.fit(_synthetic(0.30, 0.02))
    assert f['status'] == 'ok' and not f['reasons']
    assert f['kappa'] == pytest.approx(0.30, abs=0.03) and f['t'] > 10 and f['partial_r2'] > 0.8
    assert f['n'] == 60 and f['n_episodes'] == 3 and set(f['per_episode']) == {'e1', 'e2', 'e3'}
    assert f['intercepts']['e1'] == pytest.approx(-0.05, abs=0.02)


def test_ajuste_debil_o_insuficiente_dice_por_que():
    from core import scenario_pnl as SP
    f = SP.fit(_synthetic(0.0, 0.15, seed=4))
    assert f['status'] == 'weak' and f['reasons']
    f2 = SP.fit(_synthetic(0.3, 0.02, n_per=3, eps=('e1',)))
    assert f2['status'] == 'insufficient' and any('episodes_with_data' in r for r in f2['reasons'])
    f3 = SP.fit([dict(p, y=None) for p in _synthetic(0.3, 0.02)])
    assert f3['status'] == 'insufficient' and f3['n'] == 0


# ── traducción ───────────────────────────────────────────────────────────────
CAL_OK = {'kernel_params_semver': '1.0.0', 'rules': {'band_z': 1.645}, 'status': 'proposed',
          'episodes': [{'id': 'e1', 'label_es': 'x', 'label_en': 'x', 'proposed': True}],
          'fit': {'status': 'ok', 'kappa': 0.2, 'kappa_se': 0.05, 'resid_sd': 0.1, 'n': 40, 'n_episodes': 3,
                  'r2': 0.5, 'partial_r2': 0.4, 'impact_max': 0.5, 'reasons': []}}


def test_traduccion_con_banda():
    from core import scenario_pnl as SP
    imp = {'Nvidia': 50.0, 'Apple': 10.0, 'TSMC': 100.0}
    pos = [{'id': 'Nvidia', 'usd': 10000}, {'id': 'Apple', 'usd': 5000}, {'id': 'Ford', 'usd': 1000},
           {'id': None, 'symbol': 'ZZZ', 'usd': 300}, {'id': 'Intel', 'usd': 0}]
    r = SP.translate(imp, pos, cal=CAL_OK, ref=('kernel.calibration@9.9.9', 'h'), kernel_semver='1.0.0')
    expo = 10000 * 0.5 + 5000 * 0.1
    assert r['status'] == 'ok' and r['pnl_usd'] == pytest.approx(-0.2 * expo)
    band = 1.645 * math.sqrt((0.05 * expo) ** 2 + 0.1 ** 2 * (10000 ** 2 + 5000 ** 2))
    assert r['band_usd'] == pytest.approx(band, abs=0.01)
    assert r['lo_usd'] < r['pnl_usd'] < r['hi_usd'] and r['total_usd'] == 16300
    assert r['hit_positions'] == 2 and r['unmapped'] == ['ZZZ'] and r['extrapolated'] is False
    assert r['calibration']['artifact'] == 'kernel.calibration@9.9.9'
    # un golpe mayor que el máximo medido se avisa (extrapolación)
    r2 = SP.translate({'Nvidia': 90.0}, [{'id': 'Nvidia', 'usd': 1000}], cal=CAL_OK, ref=('x', 'h'),
                      kernel_semver='1.0.0')
    assert r2['extrapolated'] is True


def test_sin_cifra_cuando_no_corresponde():
    from core import scenario_pnl as SP
    imp, pos = {'Nvidia': 50.0}, [{'id': 'Nvidia', 'usd': 1000}]
    weak = json.loads(json.dumps(CAL_OK))
    weak['fit'].update(status='weak', reasons=['t 0.2 < 2.0'])
    for cal, st, ks in ((None, 'uncalibrated', '1.0.0'), ({}, 'uncalibrated', '1.0.0'), (weak, 'weak', '1.0.0'),
                        (CAL_OK, 'kernel_mismatch', '2.0.0')):
        r = SP.translate(imp, pos, cal=cal, ref=('a', 'h') if cal is not None else ('a', 'h'), kernel_semver=ks)
        assert r['status'] == st and r['pnl_usd'] is None and r['band_usd'] is None, st
        assert r['note_es'] and r['note_en']
    r = SP.translate(imp, [], cal=CAL_OK, ref=('a', 'h'), kernel_semver='1.0.0')
    assert r['status'] == 'no_positions' and r['pnl_usd'] is None


# ── el artefacto de hoy: reproducible y honesto ──────────────────────────────
def test_artefacto_reproducible_y_debil_hoy():
    import calibrate_kernel as CK

    from core import governance
    from core import scenario_pnl as SP
    assert CK.check() == 0
    doc = json.load(open(os.path.join(ROOT, 'governance', 'artifacts', 'kernel.calibration@1.0.0.json'),
                         encoding='utf-8'))
    p = doc['params']
    assert p['status'] == 'proposed' and all(e['proposed'] for e in p['episodes'])
    assert [e['id'] for e in p['episodes']] == ['chip_shortage_2021', 'export_controls_2022', 'taiwan_quake_2024']
    assert p['kernel_params_semver'] == '1.0.0' and p['inputs_file'] == 'data/calibration/inputs.json'
    assert p['fit']['status'] == 'weak' and p['fit']['reasons']
    # 2021 no tiene precios en la historia disponible: se DICE (cobertura), no se inventa
    cov = {e['id']: e['coverage'] for e in p['episodes']}
    assert cov['chip_shortage_2021']['measured'] == 0 and cov['export_controls_2022']['measured'] > 0
    # vigente: la app no da cifra en dinero
    cal, ref = SP.calibration()
    assert ref[0] == 'kernel.calibration@1.0.0' and governance.artifact_semver('kernel.calibration') == '1.0.0'
    r = SP.translate({'Nvidia': 60.0}, [{'id': 'Nvidia', 'usd': 1000}])
    assert r['status'] == 'weak' and r['pnl_usd'] is None and r['calibration']['n_episodes'] == 2


def test_el_script_de_calibracion_de_punta_a_punta_sin_red(tmp_path, monkeypatch):
    """prepare (impactos del kernel en el snapshot) → fetch (Yahoo FALSO, sin base) → fit: con precios sintéticos
    en los que la caída SÍ es −0,4 × impacto, el ajuste lo encuentra y el artefacto se escribe con su hash."""
    import calibrate_kernel as CK

    from core import prices_store as PS
    monkeypatch.setattr(PS, 'db_on', lambda: False)
    eps = [dict(e) for e in CK.EPISODES[1:]]
    inp = CK.prepare(kernel='1.0.0', episodes=eps)
    assert all(len(e['sample']) >= 10 for e in inp['episodes'])
    impact_of = {}
    for e in inp['episodes']:
        for s in e['sample']:
            impact_of.setdefault(e['id'], {})[s['symbol']] = s['impact_pct'] / 100.0
    rng = random.Random(9)

    def series(sym):
        days, px = [], []
        d0 = date(2022, 9, 1)
        for k in range(700):
            d = d0 + timedelta(days=k)
            if d.weekday() >= 5:
                continue
            p = 100.0 * (1 + rng.gauss(0, 0.002))           # ruido chico (una serie plana es «congelada»)
            for e in inp['episodes']:
                hit = impact_of[e['id']].get(sym)
                t0, t1 = date.fromisoformat(e['t0']), date.fromisoformat(e['t1'])
                if hit is not None and t0 < d <= t1:
                    p *= (1 - 0.4 * hit)                      # la caída del episodio: −0,4 × impacto
            days.append(d)
            px.append(p)
        return days, px

    def getter(url, params=None, timeout=15):
        sym = url.rsplit('/', 1)[-1]
        days, px = series(sym)
        ts = [int(datetime(d.year, d.month, d.day, 15, tzinfo=timezone.utc).timestamp()) for d in days]
        return {'chart': {'result': [{'timestamp': ts, 'meta': {'currency': 'USD', 'exchangeTimezoneName': 'UTC',
                                                                 'currentTradingPeriod': {'regular': {'start': 0, 'end': 1}}},
                                      'indicators': {'quote': [{'close': px, 'open': px, 'high': px, 'low': px,
                                                                'volume': [1] * len(px)}],
                                                     'adjclose': [{'adjclose': px}]}}]}}, None
    CK.fetch(inp, getter=getter, use_db=False)
    assert all(v['closes'] for v in inp['prices'].values())
    path = tmp_path / 'inputs.json'
    path.write_text(json.dumps(inp, sort_keys=True), encoding='utf-8')
    doc = CK.build_artifact(json.loads(path.read_text(encoding='utf-8')), str(path), '7.0.0')
    f = doc['params']['fit']
    # revisión lote I: prepare usa el grafo de HOY para episodios viejos (mirada adelante) → el ajuste se encuentra
    # (κ ≈ 0,4) pero NUNCA queda 'ok' y lo dice; con un grafo «tal como se conocía en t0» sí podría
    assert doc['params']['graph']['graph_asof'] is False
    assert f['status'] == 'weak' and f['kappa'] == pytest.approx(0.4, abs=0.06), f
    assert any(r.startswith('look-ahead') for r in f['reasons']) and len(f['reasons']) == 1
    asof = json.loads(path.read_text(encoding='utf-8'))
    asof['graph']['graph_asof'] = True
    assert CK.fit_inputs(asof)[0]['status'] == 'ok'
    assert doc['params']['inputs_sha256'] == CK.sha256_of(json.loads(path.read_text(encoding='utf-8')))
    assert doc['id'] == 'kernel.calibration' and doc['change_kind'] == 'initial'


# ── servidor real (snapshot, sin base) ───────────────────────────────────────
@pytest.fixture
def srv(monkeypatch):
    import ontology.db as odb
    import server
    from core import http as h
    from core.hotviews import builder, registry
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    registry.reset()
    builder.build_once()
    with h._rate_lock:
        h._rate_buckets.clear()
    yield server.app.test_client()
    registry.reset()


def test_endpoint_scenario_pnl_sin_cifra_hoy_y_validaciones(srv):
    r = srv.post('/api/hot/scenario_pnl', json={'shocks': [{'id': 'TSMC', 'magnitude': 1}],
                                                'positions': [{'id': 'Nvidia', 'usd': 1000}, {'symbol': 'AAPL', 'usd': 500},
                                                              {'symbol': 'ZZZZ', 'usd': 10}], 'record': False})
    assert r.status_code == 200
    d = r.get_json()['data']
    assert d['shocks'] == [{'id': 'TSMC', 'magnitude': 1.0}] and d['affected'] > 100
    p = d['pnl']
    assert p['status'] == 'weak' and p['pnl_usd'] is None and p['band_usd'] is None
    assert p['calibration']['artifact'] == 'kernel.calibration@1.0.0' and p['note_en']
    assert r.get_json()['view']['generation']
    assert srv.post('/api/hot/scenario_pnl', json={'positions': []}).status_code == 400
    assert srv.post('/api/hot/scenario_pnl', json={'shocks': ['TSMC']}).status_code == 400
    assert srv.post('/api/hot/scenario_pnl', json={'shocks': ['zz-no'], 'positions': []}).status_code == 400
    assert srv.post('/api/hot/scenario_pnl', json={'shocks': ['TSMC'], 'positions': [], 'factors': 'x'}).status_code == 400


def test_endpoint_con_calibracion_buena_da_la_cifra_del_kernel(srv, monkeypatch):
    """Con un κ que SÍ pasara las reglas, la cifra es −κ × Σ usd × impacto del MISMO kernel de /scenario."""
    from core import scenario_pnl as SP
    monkeypatch.setattr(SP, 'calibration', lambda: (CAL_OK, ('kernel.calibration@t', 'h')))
    body = {'shocks': [{'id': 'TSMC', 'magnitude': 1}], 'positions': [{'id': 'Nvidia', 'usd': 1000}], 'record': False}
    p = srv.post('/api/hot/scenario_pnl', json=body).get_json()['data']['pnl']
    sc = srv.post('/api/hot/scenario', json={'shocks': [{'id': 'TSMC', 'magnitude': 1}], 'full': True}).get_json()['data']
    hit = sc['impacts']['Nvidia'] / 100.0
    assert p['status'] == 'ok' and p['pnl_usd'] == pytest.approx(-0.2 * 1000 * hit, abs=0.01)
    assert p['positions'][0]['impact_pct'] == sc['impacts']['Nvidia']


def test_ficha_whatif_cita_la_version_de_kappa(monkeypatch):
    """ledger_whatif arma la ficha (async) con la política kernel.calibration@<semver> citada."""
    from core import decisions
    from matrix import api as MA
    captured = {}
    monkeypatch.setattr(decisions, 'submit_async', lambda build: captured.setdefault('ctx', build()) and True)
    from flask import Flask
    with Flask('t').test_request_context('/api/hot/scenario_pnl', method='POST'):
        MA.ledger_whatif('whatif.shock', {'shock': ['TSMC'], 'endpoint': '/api/hot/scenario_pnl'}, {'TSMC': 100.0})
    ctx = captured['ctx']
    assert any(k[0] == 'policy' and k[2].startswith('kernel.calibration@') for k in ctx.refs), ctx.refs


def test_la_linea_dice_cuantas_posiciones_quedaron_sin_valorar():
    """Revisión lote I: posiciones sin precio (no_price) o que el servidor no ubicó (unmapped) NO están en la cifra →
    la línea lo dice (ES/EN); y si faltan cotizaciones se repinta UNA vez cuando llegan (evento khipu:quotes)."""
    import shutil
    import subprocess
    node = shutil.which('node')
    if not node:
        pytest.skip('node no disponible')
    js = r"""
const vm = require('vm'), fs = require('fs');
const listeners = {};
const win = { LANG: 'es', localStorage: { getItem() { return null; } },
  addEventListener(n, f) { (listeners[n] = listeners[n] || []).push(f); },
  removeEventListener(n, f) { listeners[n] = (listeners[n] || []).filter(x => x !== f); },
  NODE_BY_ID: { Nvidia: { id: 'Nvidia', mkt: 'NVDA' }, SpaceX: { id: 'SpaceX' } },
  MKT: { pos: { Nvidia: { sh: 10 }, SpaceX: { sh: 5 } }, quotes: { NVDA: { close: 100 } } } };
const sb = { window: win, console, setTimeout, clearTimeout, Promise, JSON, Object, Math, Map, Number, String, Array };
vm.createContext(sb);
vm.runInContext(fs.readFileSync(process.argv[2] + '/engine/hotclient.js', 'utf8'), sb);
const H = win.KhipuHot;
const ok = { status: 'ok', pnl_usd: -120, band_usd: 40, calibration: { n_episodes: 3 }, unmapped: ['ZZZ'] };
const out = {};
out.es = H.pnlLineHTML({ ok: true, no_price: 1, data: { pnl: ok } });
win.LANG = 'en';
out.en = H.pnlLineHTML({ ok: true, no_price: 1, data: { pnl: Object.assign({}, ok, { unmapped: [] }) } });
out.full = H.pnlLineHTML({ ok: true, no_price: 0, data: { pnl: Object.assign({}, ok, { unmapped: [] }) } });
// sin ninguna cotización todavía: la línea queda oculta y espera a khipu:quotes
win.MKT.quotes = {};
const el = { style: {}, innerHTML: '', isConnected: true };
H.pnlLine(el, { targets: ['TSMC'], severity: 100, kind: 'collapse' });
out.waiting = (listeners['khipu:quotes'] || []).length;
out.hidden = el.style.display;
console.log(JSON.stringify(out));
"""
    import os as _os
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as fh:
        fh.write(js)
    try:
        r = subprocess.run([node, fh.name, ROOT], capture_output=True, text=True, timeout=30)
    finally:
        _os.unlink(fh.name)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert 'sin valorar: 2 posiciones' in out['es'] and 'not valued: 1 position<' in out['en']
    assert 'not valued' not in out['full'] and 'Your portfolio' in out['en']
    assert out['waiting'] == 1 and out['hidden'] == 'none'
