#!/usr/bin/env python3
"""scripts/calibrate_kernel.py — calibra κ (escenario → dinero) con episodios reales (BRECHAS L2-13 / PROP-16; batch I3).

Tres pasos, cada uno reproducible y SIN IA:

    # 1) muestra: impactos del kernel (snapshot data/grafo_v0.json, kernel.params indicado, factores latentes) por
    #    episodio + qué empresas cotizadas se miden. Escribe el archivo de ENTRADAS sin precios.
    python scripts/calibrate_kernel.py prepare --out data/calibration/inputs.json [--kernel 1.0.0]

    # 2) precios: cierres ajustados de cada símbolo alrededor de cada ventana — historia propia (prices_eod, si hay
    #    DATABASE_URL) y, si no la cubre, Yahoo (fechas exactas). Se guardan UNA vez en el archivo de entradas.
    python scripts/calibrate_kernel.py fetch --inputs data/calibration/inputs.json

    # 3) ajuste: SOLO lee el archivo de entradas (su sha256 queda en el artefacto) y escribe
    #    governance/artifacts/kernel.calibration@<semver>.json (registro que solo crece) — luego
    #    `python scripts/build_governance.py --write`.
    python scripts/calibrate_kernel.py fit --inputs data/calibration/inputs.json --semver 1.0.0 [--write]
    python scripts/calibrate_kernel.py check     # el artefacto más nuevo se reproduce desde su archivo de entradas

Los episodios por defecto son los que propone BRECHAS #11 (escasez de chips 2021, controles de exportación de oct-2022,
terremoto de Taiwán de abr-2024): son PROPUESTAS (fechas, semillas y magnitudes son supuestos para revisar), y el
artefacto lo dice. Si el ajuste es débil, el artefacto lo guarda igual con `fit.status: weak` y la app NO da cifra.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SCHEMA = 'khipus.calibration.inputs/1'
BENCHMARK = 'SPY'
SAMPLE_TOP = 12          # las 12 más golpeadas…
SAMPLE_SPREAD = 8        # …+ 8 repartidas en el resto (para que el impacto varíe)
MIN_IMPACT_PCT = 1.0

# PROPUESTOS (BRECHAS #11, decisión por defecto): revísalos. Las magnitudes son SUPUESTOS, no datos.
EPISODES = [
    {'id': 'chip_shortage_2021', 'label_es': 'Escasez de chips 2021', 'label_en': '2021 chip shortage',
     'event_date': '2021-02-01', 't0': '2021-01-29', 't1': '2021-04-30',
     'seeds': [{'id': 'TSMC', 'magnitude': 0.3}, {'id': 'Samsung', 'magnitude': 0.3}, {'id': 'GF', 'magnitude': 0.3},
               {'id': 'SMIC', 'magnitude': 0.3}],
     'note_es': 'Golpe gradual: ventana aproximada (feb-abr 2021). Semillas = fundiciones, magnitud 0,3 supuesta.',
     'note_en': 'Gradual shock: approximate window (Feb-Apr 2021). Seeds = foundries, magnitude 0.3 assumed.',
     'proposed': True},
    {'id': 'export_controls_2022', 'label_es': 'Controles de exportación EE. UU., oct-2022',
     'label_en': 'US export controls, Oct 2022', 'event_date': '2022-10-07', 't0': '2022-10-06', 't1': '2022-11-04',
     'seeds': [{'id': 'Nvidia', 'magnitude': 0.25}, {'id': 'AMD', 'magnitude': 0.25}, {'id': 'ASML', 'magnitude': 0.25}],
     'note_es': 'Semillas = exposición a China de Nvidia/AMD/ASML; magnitud 0,25 supuesta (no es un dato).',
     'note_en': 'Seeds = China exposure of Nvidia/AMD/ASML; magnitude 0.25 assumed (not a data point).',
     'proposed': True},
    {'id': 'taiwan_quake_2024', 'label_es': 'Terremoto de Taiwán, abr-2024', 'label_en': 'Taiwan earthquake, Apr 2024',
     'event_date': '2024-04-03', 't0': '2024-04-02', 't1': '2024-04-30',
     'seeds': [{'id': 'TSMC', 'magnitude': 0.1}],
     'note_es': 'Semilla = TSMC (paradas breves de fábricas); magnitud 0,1 supuesta.',
     'note_en': 'Seed = TSMC (brief fab stoppages); magnitude 0.1 assumed.',
     'proposed': True},
]


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str)


def sha256_of(obj):
    return hashlib.sha256(canonical(obj).encode('utf-8')).hexdigest()


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def us_listed(sym):
    """Solo cotizaciones en EE. UU. (acciones y ADR/OTC en USD): se comparan con SPY el mismo día y sin moneda."""
    return bool(sym) and '.' not in sym and sym.replace('-', '').isalnum() and not sym.isdigit()


# ── paso 1: impactos y muestra ───────────────────────────────────────────────────────────────────────────────────
def episode_impacts(core, episode):
    import numpy as np

    from core.hotviews.views import impact
    x0 = np.zeros(len(core.ids))
    for s in episode['seeds']:
        oid = core.resolve(s['id'])
        if oid is not None:
            x0[core.idx[oid]] = max(x0[core.idx[oid]], float(s['magnitude']))
    sc = impact.scenario(core, x0, factors='active', top=1)
    return sc['impacts']


def mkt_map(data):
    """{id: ticker principal (`mkt`)} de las empresas del grafo de lectura (catálogo/snapshot)."""
    return {n['id']: str(n.get('mkt') or '').strip().upper() for n in (getattr(data, 'nodes', None) or [])
            if n.get('id') and n.get('mkt')}


def sample_for(core, impacts, seeds, tickers):
    seed_ids = {core.resolve(s['id']) for s in seeds}
    rows = []
    for oid, pct in impacts.items():
        sym = tickers.get(oid, '')
        if pct < MIN_IMPACT_PCT or not us_listed(sym) or sym == BENCHMARK:
            continue
        rows.append({'id': oid, 'symbol': sym, 'impact_pct': round(float(pct), 4), 'seed': oid in seed_ids})
    rows.sort(key=lambda r: (-r['impact_pct'], r['id']))
    seen, out = set(), []
    for r in rows:                            # un símbolo una vez (dos ids con el mismo ticker: el más golpeado)
        if r['symbol'] not in seen:
            seen.add(r['symbol'])
            out.append(r)
    head, rest = out[:SAMPLE_TOP], out[SAMPLE_TOP:]
    if rest and SAMPLE_SPREAD:
        step = max(1, len(rest) // SAMPLE_SPREAD)
        head += rest[::step][:SAMPLE_SPREAD]
    return head


def prepare(kernel='1.0.0', episodes=None, snapshot=None):
    from core import governance
    from core.hotviews import source
    from core.hotviews.views import graph_core
    eps = [dict(e) for e in (episodes or EPISODES)]
    with governance.counterfactual({'kernel.params': kernel}):
        data = snapshot or source.load_snapshot()
        core = graph_core.build(data)
        tickers = mkt_map(data)
        for ep in eps:
            imp = episode_impacts(core, ep)
            ep['sample'] = sample_for(core, imp, ep['seeds'], tickers)
            ep['reach_1pct'] = sum(1 for v in imp.values() if v >= 1.0)
        kref = governance.policy_ref('kernel.params')
    return {'schema': SCHEMA, 'created_at': _now(),
            # revisión lote I: los impactos de TODOS los episodios salen del grafo de HOY (no del conocido en t0):
            # sesgo de mirada adelante. Se dice, y fit_inputs no deja que un ajuste así quede 'ok'.
            'graph': {'source': getattr(data, 'source', 'snapshot'), 'lineage': getattr(data, 'lineage', None),
                      'graph_asof': False},
            'kernel_params': {'artifact': kref[0], 'hash': kref[1], 'semver': kernel}, 'factors': 'active',
            'benchmark': {'symbol': BENCHMARK}, 'measure': 'relative_drawdown',
            'episodes': eps, 'prices': {}}


# ── paso 2: precios (historia propia → Yahoo con fechas exactas) ───────────────────────────────────────────────
def _window_bounds(inputs, pad_days=14):
    from datetime import date, timedelta
    lo = min(date.fromisoformat(e['t0']) for e in inputs['episodes']) - timedelta(days=pad_days)
    hi = max(date.fromisoformat(e['t1']) for e in inputs['episodes']) + timedelta(days=1)
    return lo, hi


def _slice(closes, inputs, pad_days=14):
    from datetime import date, timedelta
    keep = {}
    for e in inputs['episodes']:
        a = (date.fromisoformat(e['t0']) - timedelta(days=pad_days)).isoformat()
        b = e['t1']
        for d, v in closes.items():
            if a <= d <= b:
                keep[d] = v
    return dict(sorted(keep.items()))


def fetch(inputs, getter=None, use_db=True):
    """Rellena inputs['prices'][símbolo] = {source, frequency, currency, closes{fecha: cierre ajustado}} solo con las
    fechas de las ventanas. Nunca inventa: un símbolo sin datos queda con closes vacío y error."""
    from datetime import datetime as _dt
    from datetime import time as _time

    from core import prices_store as PS
    syms = sorted({s['symbol'] for e in inputs['episodes'] for s in e['sample']} | {inputs['benchmark']['symbol']})
    lo, hi = _window_bounds(inputs)
    for sym in syms:
        if (inputs['prices'].get(sym) or {}).get('closes'):
            continue
        closes, src, cur, err = {}, None, None, None
        if use_db and PS.db_on():
            try:
                from ontology.db import session_scope
                with session_scope() as s:
                    rows = PS.load_series(s, sym, start=lo)
                closes = {r['date'].isoformat(): r['adj'] for r in rows if r.get('adj') and r['adj'] > 0}
                cur = next((r['currency'] for r in rows if r.get('currency')), None)
                src = f'khipus_eod:{PS.SOURCE}'
            except Exception as e:  # noqa: BLE001
                err = f'db: {type(e).__name__}'
        if not _covers_all(closes, inputs):
            now = _dt.combine(hi, _time(23, 0), tzinfo=timezone.utc)
            years = (hi - lo).days / 365.25
            f = PS.fetch_chart(sym, getter=getter, now=now, years=years)
            closes = {r['date'].isoformat(): (r['adj_close'] or r['close']) for r in f['rows']}
            cur, src, err = f.get('currency'), 'yahoo_adjclose', f.get('error')
        inputs['prices'][sym] = {'source': src, 'frequency': 'daily', 'currency': cur,
                                 'closes': _slice(closes, inputs), **({'error': err} if err and not closes else {})}
    inputs['prices_fetched_at'] = _now()
    return inputs


def _covers_all(closes, inputs):
    from core.scenario_pnl import close_on_or_before
    if not closes:
        return False
    for e in inputs['episodes']:
        if close_on_or_before(closes, e['t0'])[0] is None or not any(e['t0'] < d <= e['t1'] for d in closes):
            return False
    return True


# ── paso 3: ajuste → artefacto ───────────────────────────────────────────────────────────────────────────────────
def fit_inputs(inputs, rules=None):
    from core import scenario_pnl as SP
    pts = SP.points_from_inputs(inputs)
    res = SP.fit(pts, rules)
    if (inputs.get('graph') or {}).get('graph_asof') is False:      # grafo de hoy para episodios viejos → nunca 'ok'
        res['reasons'] = list(res.get('reasons') or []) + [
            "look-ahead: episode impacts use today's graph, not the graph known at t0 (graph_asof false)"]
        if res.get('status') == 'ok':
            res['status'] = 'weak'
    cov = {}
    for e in inputs['episodes']:
        mine = [p for p in pts if p['episode'] == e['id']]
        cov[e['id']] = {'sampled': len(mine), 'measured': sum(1 for p in mine if p['y'] is not None)}
    return res, pts, cov


def build_artifact(inputs, inputs_path, semver, rules=None, parent=None):
    from core import scenario_pnl as SP
    r = dict(SP.DEFAULT_RULES, **(rules or {}))
    res, pts, cov = fit_inputs(inputs, r)
    eps = [{k: e[k] for k in ('id', 'label_es', 'label_en', 'event_date', 't0', 't1', 'seeds', 'note_es', 'note_en',
                              'proposed')} | {'coverage': cov[e['id']]} for e in inputs['episodes']]
    srcs = sorted({(v.get('source') or '?') + '/' + (v.get('frequency') or '?') for v in inputs['prices'].values()})
    doc = {
        'id': SP.ARTIFACT, 'semver': semver, 'kind': 'calibration',
        'change_kind': 'initial' if parent is None else 'minor',
        'parent': parent,
        'params': {
            'status': 'proposed',
            'measure': SP.MEASURE, 'benchmark': inputs['benchmark']['symbol'],
            'kernel_params_semver': inputs['kernel_params']['semver'],
            'kernel_params_hash': inputs['kernel_params']['hash'],
            'factors': inputs.get('factors', 'active'),
            'graph': inputs.get('graph'),
            'episodes': eps,
            'rules': r,
            'inputs_file': os.path.relpath(inputs_path, ROOT).replace(os.sep, '/'),
            'inputs_sha256': sha256_of(inputs),
            'price_sources': srcs,
            'fit': res,
            'points': [[p['episode'], p['symbol'], p['impact'], p['y']] for p in pts],
        },
    }
    k = res.get('kappa')
    if res['status'] == 'ok':
        es = (f"κ = {k} (error {res['kappa_se']}, R² parcial {res['partial_r2']}, n = {res['n']}, "
              f"{res['n_episodes']} episodios). La app traduce escenarios a dinero con banda.")
        en = (f"κ = {k} (s.e. {res['kappa_se']}, partial R² {res['partial_r2']}, n = {res['n']}, "
              f"{res['n_episodes']} episodes). The app translates scenarios into money with a band.")
    else:
        es = ('Ajuste DÉBIL o insuficiente (' + '; '.join(res['reasons']) + '): la app NO da cifras en dinero y lo '
              'dice. Hace falta más historia o episodios mejores.')
        en = ('WEAK or insufficient fit (' + '; '.join(res['reasons']) + '): the app gives NO money figures and says '
              'so. It needs more history or better episodes.')
    doc['changelog_es'] = 'Calibración de κ (escenario → dinero) con episodios PROPUESTOS (BRECHAS #11). ' + es
    doc['changelog_en'] = 'κ calibration (scenario → money) on PROPOSED episodes (BRECHAS #11). ' + en
    return doc


def _latest_doc():
    from core import governance as G
    docs = G.scan_repo()
    return G.latest_per_id(docs).get('kernel.calibration')


def check():
    """El artefacto más nuevo se reproduce desde su archivo de entradas (hash y ajuste idénticos)."""
    doc = _latest_doc()
    if doc is None:
        print('sin kernel.calibration en el repositorio')
        return 0
    p = doc['params']
    path = os.path.join(ROOT, p['inputs_file'])
    with open(path, encoding='utf-8') as fh:
        inputs = json.load(fh)
    probs = []
    if sha256_of(inputs) != p['inputs_sha256']:
        probs.append(f"{p['inputs_file']}: su sha256 no es el del artefacto (¿se editó?)")
    res, _pts, _cov = fit_inputs(inputs, p['rules'])
    if canonical(res) != canonical(p['fit']):
        probs.append('el ajuste recalculado no coincide con el guardado en el artefacto')
    for x in probs:
        print('✗', x)
    if not probs:
        print(f"✓ kernel.calibration@{doc['semver']} se reproduce desde {p['inputs_file']} ({p['fit']['status']})")
    return 1 if probs else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    a1 = sub.add_parser('prepare')
    a1.add_argument('--out', required=True)
    a1.add_argument('--kernel', default='1.0.0')
    a2 = sub.add_parser('fetch')
    a2.add_argument('--inputs', required=True)
    a2.add_argument('--no-db', action='store_true')
    a3 = sub.add_parser('fit')
    a3.add_argument('--inputs', required=True)
    a3.add_argument('--semver', required=True)
    a3.add_argument('--write', action='store_true')
    sub.add_parser('check')
    a = ap.parse_args(argv)
    if a.cmd == 'prepare':
        inp = prepare(kernel=a.kernel)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, 'w', encoding='utf-8') as fh:
            json.dump(inp, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write('\n')
        for e in inp['episodes']:
            print(e['id'], len(e['sample']), [s['symbol'] for s in e['sample']])
        return 0
    if a.cmd == 'fetch':
        with open(a.inputs, encoding='utf-8') as fh:
            inp = json.load(fh)
        fetch(inp, use_db=not a.no_db)
        with open(a.inputs, 'w', encoding='utf-8') as fh:
            json.dump(inp, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write('\n')
        missing = [s for s, v in inp['prices'].items() if not v.get('closes')]
        print('precios:', len(inp['prices']), 'sin datos:', missing)
        return 0
    if a.cmd == 'fit':
        with open(a.inputs, encoding='utf-8') as fh:
            inp = json.load(fh)
        prev = _latest_doc()
        doc = build_artifact(inp, os.path.abspath(a.inputs), a.semver,
                             parent=f"kernel.calibration@{prev['semver']}" if prev else None)
        print(json.dumps(doc['params']['fit'], indent=1, ensure_ascii=False))
        if a.write:
            from core import governance as G
            path = G.artifact_path('kernel.calibration', a.semver)
            if os.path.exists(path):
                raise SystemExit(f'{path} ya existe (el registro solo crece: usa otra versión)')
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
            print('escrito', os.path.relpath(path, ROOT), '→ ahora: python scripts/build_governance.py --write')
        return 0
    return check()


if __name__ == '__main__':
    sys.exit(main())
