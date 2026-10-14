"""tests/test_genui_builders.py — CONSTRUCTORES deterministas de bloques (core/genui/builders.py) y el guardián de
PROCEDENCIA (core/genui/provenance.py) — docs/CHAT_UI_GENERATIVA.md §5.2, §5.5 y §10.1, F1 pasos 7-11.

Cada resultado grabado (tests/fixtures/genui/tools/*.json: reales del snapshot o MUESTRAS rotuladas `sample: true`)
produce su salida DORADA (tests/golden/genui_<fixture>.json). Para regenerarlas a propósito:
    GENUI_UPDATE_GOLDEN=1 pytest tests/test_genui_builders.py
(un cambio de salida también cambia la dorada de genui.build@1 → nace @2; ver core/impls.py).

Además: toda cifra de cada bloque está en el resultado citado; quitarla del resultado hace que el bloque se descarte;
`v: null` siempre lleva su motivo; la cascada solo con src hot_kernel; los «ganadores» con su % de DAÑO; el esquema
de cada bloque; ≤ 5 ms por bloque.
"""
import copy
import glob
import json
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import genui  # noqa: E402
from core.genui import builders as B  # noqa: E402
from core.genui import provenance as P  # noqa: E402
from core.genui import validate as V  # noqa: E402

FIX = sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools', '*.json')))
GOLD = os.path.join(ROOT, 'tests', 'golden')
UPDATE = os.getenv('GENUI_UPDATE_GOLDEN') == '1'


def _load(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def _build(doc, lang='es'):
    b = B.Ctx(lang, 0, 'F1', 'args', meta={'labels': {'Nvidia': 'Nvidia', 'AMD': 'AMD'}})
    blocks = B.BUILDERS[doc['tool']](copy.deepcopy(doc['result']), b)
    calls = [(doc['tool'], doc.get('args'), True, doc['result'])]
    out = []
    for blk in blocks:
        ok, why, _n = genui._check(blk, calls)
        assert ok, (doc['tool'], blk['type'], why)
        out.append(genui._strip(blk))
    return out


@pytest.mark.parametrize('path', FIX, ids=[os.path.basename(p)[:-5] for p in FIX])
def test_salida_dorada(path):
    doc = _load(path)
    out = {'es': _build(doc, 'es'), 'en': _build(doc, 'en')}
    gp = os.path.join(GOLD, 'genui_' + os.path.basename(path))
    if UPDATE or not os.path.exists(gp):
        if not UPDATE:
            pytest.fail(f'falta la dorada {os.path.relpath(gp, ROOT)} (GENUI_UPDATE_GOLDEN=1 para crearla)')
        with open(gp, 'w', encoding='utf-8') as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write('\n')
    assert _load(gp) == json.loads(json.dumps(out)), 'la salida del constructor cambió: ¿a propósito? → regenerar y @2'


def test_hay_fixture_por_constructor():
    tools = {_load(p)['tool'] for p in FIX}
    assert tools == set(B.BUILDERS), sorted(set(B.BUILDERS) ^ tools)


@pytest.mark.parametrize('path', FIX, ids=[os.path.basename(p)[:-5] for p in FIX])
def test_cada_bloque_cumple_esquema_y_procedencia(path):
    doc = _load(path)
    for blk in _build(doc):
        assert V.errors(blk, 'Block') == [], (blk['type'], V.errors(blk, 'Block'))
        assert blk.get('prov', {}).get('name') == doc['tool']
        # todo Figure con v null lleva su motivo; con v número, su hora
        def walk(x):
            if isinstance(x, dict):
                if 'v' in x and 'unit' in x and 'src' in x:
                    if x['v'] is None:
                        assert x.get('missing_reason', {}).get('es') and x['missing_reason'].get('en')
                    else:
                        assert x.get('as_of')
                for y in x.values():
                    walk(y)
            elif isinstance(x, list):
                for y in x:
                    walk(y)
        walk(blk)


def _first_figure_value(blk):
    """La primera cifra COPIADA tal cual (no las derivadas por una transformación declarada: severidad = magnitud ×
    100, umbral del kernel × 100 — quitar su número no quita la fuente de la que se derivan)."""
    figs = [f for f in P.figures_of(blk) if f[0][-1] not in ('severity', 'threshold_pct')]
    return figs[0] if figs else None


def _drop_number(obj, value):
    """Copia del resultado SIN ese número (se cambia por un texto): la cifra queda sin dueño."""
    if isinstance(obj, dict):
        return {k: _drop_number(v, value) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_drop_number(v, value) for v in obj]
    if isinstance(obj, (int, float)) and not isinstance(obj, bool) and abs(float(obj) - float(value)) < 1e-6:
        return 'quitado'
    return obj


@pytest.mark.parametrize('path', [p for p in FIX if 'get_news' not in p and 'research' not in p],
                         ids=[os.path.basename(p)[:-5] for p in FIX if 'get_news' not in p and 'research' not in p])
def test_cifra_quitada_del_resultado_descarta_el_bloque(path):
    doc = _load(path)
    b = B.Ctx('es', 0, 'F1', 'args', meta={'labels': {'Nvidia': 'Nvidia', 'AMD': 'AMD'}})
    for blk in B.BUILDERS[doc['tool']](copy.deepcopy(doc['result']), b):
        fv = _first_figure_value(genui._strip(blk))
        if fv is None:
            continue
        _path, value = fv
        tampered = _drop_number(doc['result'], value)
        ok, why, _ = genui._check(blk, [(doc['tool'], None, True, tampered)])
        assert not ok and why == 'no_provenance', (doc['tool'], blk['type'], value)


def test_cifra_inventada_en_el_bloque_se_descarta():
    doc = _load(os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools', 'get_company__nvidia.json'))
    b = B.Ctx('es', 0, 'F1', '')
    tiles = B.b_get_company(copy.deepcopy(doc['result']), b)[0]
    tiles['data']['items'][0]['value']['v'] = 233.95          # una cifra que la herramienta nunca dio
    ok, why, _ = genui._check(tiles, [('get_company', None, True, doc['result'])])
    assert not ok and why == 'no_provenance'


def test_sin_precio_en_vivo_no_hay_cero_falso():
    doc = _load(os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools', 'get_company__tsmc_nolive.json'))
    tiles, card = _build(doc)
    price = tiles['data']['items'][0]['value']
    assert price['v'] is None and price['missing_reason']['es'] and price['as_of'] is None
    assert card['data']['nrs']['v'] is not None and card['data']['nrs']['explain'] == 'nrs'


def test_privada_muestra_su_ultima_ronda_verificada():
    doc = _load(os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools', 'get_company__openai.json'))
    tiles, card = _build(doc)
    v = tiles['data']['items'][0]['value']
    pv = doc['result']['private_valuation']
    assert v['v'] == pv['valuation_usd_b'] and v['unit'] == 'USD_B' and v['as_of'] == pv['as_of']
    assert card['data']['listed'] is False and card['data']['private_valuation']['source_url'].startswith('https://')


def test_cascada_solo_del_kernel_y_ganadores_con_dano():
    doc = _load(os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools', 'run_scenario__tsmc.json'))
    (c,) = _build(doc)
    d = c['data']
    assert d['src'] == 'hot_kernel' and d['total'] == doc['result']['reach_1pct']
    assert d['generation'] == doc['result']['generation'] and d['kernel'] == doc['result']['kernel']['semver']
    assert sum(h['count'] for h in d['hops']) == sum(doc['result']['by_hop'].values())
    riv = d.get('least_hit_rivals') or []
    assert riv and all(set(r) == {'entity', 'damage_pct'} for r in riv)
    assert all(r['damage_pct'] < 15 for r in riv)          # la regla: rivales POCO golpeados (% de daño)
    src = {r['id']: r['impact_pct'] for r in doc['result']['least_hit_rivals']}
    assert {r['entity']['id']: r['damage_pct'] for r in riv} == src
    # nunca un % de GANANCIA: ningún campo de ganancia en el bloque
    assert 'gain' not in json.dumps(c) and 'benefit' not in json.dumps(c)
    # un choque NO del kernel no valida
    bad = copy.deepcopy(c)
    bad['data']['src'] = 'client_js'
    assert not V.is_valid(bad, 'Block')


def test_cartera_debil_sin_cifra():
    doc = _load(os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools', 'run_scenario__skhynix_positions.json'))
    (c,) = _build(doc)
    pf = c['data']['portfolio']
    st = doc['result']['portfolio']['calibrated']['status']
    if st == 'ok':
        assert pf['state'] == 'figure' and pf['value']['v'] == doc['result']['portfolio']['calibrated']['pnl_usd']
    else:
        assert pf['state'] == 'no_figure' and pf['reason']['es'] and 'value' not in pf
    ok = copy.deepcopy(doc['result'])
    ok['portfolio']['calibrated'] = {'status': 'ok', 'pnl_usd': -1234.5, 'band_usd': 310.0}
    (c2,) = B.BUILDERS['run_scenario'](ok, B.Ctx('es', 0, 'F1', ''))
    assert c2['data']['portfolio']['state'] == 'figure'
    assert c2['data']['portfolio']['value']['v'] == -1234.5 and c2['data']['portfolio']['band']['v'] == 310.0
    assert genui._check(c2, [('run_scenario', None, True, ok)])[0]


def test_linea_lttb_elige_puntos_que_existen_y_compara_en_base_100():
    doc = _load(os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools', 'get_history__nvda.json'))
    res = copy.deepcopy(doc['result'])
    import datetime
    day = datetime.date(2020, 1, 1)
    res['points'] = [{'date': (day + datetime.timedelta(days=i)).isoformat(), 'close': 100 + (i % 37) * 0.5 + i * 0.01}
                     for i in range(1400)]
    (line,) = B.b_get_history(res, B.Ctx('es', 0, 'F1', ''))
    pts = line['data']['series'][0]['points']
    assert len(pts) == B.LINE_MAX_POINTS
    src = {(p['date'], p['close']) for p in res['points']}
    assert all((d, v) in src for d, v in pts)              # LTTB elige puntos REALES
    assert pts[0][0] == res['points'][0]['date'] and pts[-1][0] == res['points'][-1]['date']
    assert genui._check(line, [('get_history', None, True, res)])[0]
    amd = _load(os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools', 'get_history__amd.json'))['result']
    pairs = [(doc['result'], B.Ctx('es', 0, 'F1', '')), (amd, B.Ctx('es', 1, 'F2', ''))]
    (cmp_,) = B.history_compare(pairs, pairs[0][1])
    assert cmp_['data']['rebased'] is True and len(cmp_['data']['series']) == 2
    assert all(s['points'][0][1] == 100.0 for s in cmp_['data']['series'])
    calls = [('get_history', None, True, doc['result']), ('get_history', None, True, amd)]
    assert genui._check(cmp_, calls)[0]
    assert cmp_['sources'] == ['F1', 'F2']


def test_comparacion_de_empresas_solo_misma_fuente():
    a = _load(os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools', 'get_company__nvidia.json'))['result']
    b = _load(os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools', 'get_company__amd.json'))['result']
    pairs = [(a, B.Ctx('es', 0, 'F1', '')), (b, B.Ctx('es', 1, 'F2', ''))]
    (cmp_,) = B.company_comparison(pairs, pairs[0][1])
    keys = [m['key'] for m in cmp_['data']['metrics']]
    assert keys[:4] == ['price', 'change', 'market_cap', 'nrs']
    nrs = next(m for m in cmp_['data']['metrics'] if m['key'] == 'nrs')
    assert nrs['better'] == 'lower' and nrs['cells'] == [a['network_risk_score']['value'], b['network_risk_score']['value']]
    assert genui._check(cmp_, [('get_company', None, True, a), ('get_company', None, True, b)])[0]
    b2 = copy.deepcopy(b)
    b2['live_market']['source'] = 'finnhub'                 # otra fuente: el precio NO va en la misma fila
    (cmp2,) = B.company_comparison([(a, B.Ctx('es', 0)), (b2, B.Ctx('es', 1))], B.Ctx('es', 0))
    assert 'price' not in [m['key'] for m in cmp2['data']['metrics']]


def test_cinco_ms_por_bloque():
    docs = [_load(p) for p in FIX]
    t0 = time.perf_counter()
    n = 0
    for _ in range(5):
        for doc in docs:
            n += len(_build(doc))
    per = (time.perf_counter() - t0) * 1000 / n
    assert per < 5.0, f'{per:.2f} ms por bloque'
