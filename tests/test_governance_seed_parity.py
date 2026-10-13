"""tests/test_governance_seed_parity.py — INFRA_OPERATIVA paso 9: PARIDAD del registro de gobernanza (0 cambios).

El paso 9 movió las constantes del kernel, del NRS, del comité, de los controles del corretaje, del guardián de
cifras, de la auto-aplicación y de Jev a artefactos versionados (governance/artifacts/*.json) que el código lee por
core/governance. Esta prueba corre esos núcleos sobre accesorios FIJOS y compara con las salidas guardadas ANTES
del cambio (tests/golden/governance_parity_v1.json, generadas con el código de antes):

  · kernel: la vista Impact completa (937 choques unitarios sobre el snapshot, con los factores latentes) →
    content_sha idéntico; ρ(T), fragilidad con el tope, el flujo del tensor (mismo kernel, solo relaciones de
    flujo) y propagate con flags no lineales;
  · NRS: core.world.client_nrs de TODOS los nodos con su grado de flujo;
  · comité: conviction_by_horizon, decide, compute_sizing (validado y no), quorum_check, mandate_from;
  · corretaje: run_checks sobre 6 contextos (perfiles, venta, límite) + effective_limits;
  · guardián de cifras: _tol en una grilla y check_numbers sobre textos;
  · valores sueltos: SAFE_AUTO, AUTO_MIN_CONFIDENCE, MIN_CONF/CONTROL_WAIT_S de Jev.

Regenerar el dorado SOLO con el código de antes (nunca para "arreglar" una diferencia):
    python -m tests.test_governance_seed_parity --write
"""
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
GOLDEN = os.path.join(ROOT, 'tests', 'golden', 'governance_parity_v1.json')


def _sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'), default=repr).encode()).hexdigest()


def _kernel():
    import numpy as np

    from core.hotviews import source
    from core.hotviews.views import graph_core, impact
    from matrix import engine as E
    from matrix import tensor as T
    data = source.load_snapshot()
    core = graph_core.build(data)
    imp = impact.build(core)
    out = {'impact_sha': imp.content_sha, 'impact_nnz': imp.nnz, 'n': len(core.ids),
           'rho': core.rho,
           'frag_sha': hashlib.sha256(np.ascontiguousarray(core.frag).tobytes()).hexdigest(),
           'top_by_sum': imp.by_sum[:15]}
    # fragilidad con factores en crisis (el tope FRAGILITY_CAP corta)
    hot = [dict(f, severity=f['severity_crisis'] or 8.0) for f in core.factors[:12]]
    fr = E.fragility(core.idx, hot)
    out['frag_crisis_sha'] = hashlib.sha256(np.ascontiguousarray(fr).tobytes()).hexdigest()
    out['frag_crisis_max'] = float(fr.max())
    shocks = [core.ids[i] for i in range(0, len(core.ids), max(1, len(core.ids) // 6))][:6]
    res = {}
    for nl in (False, True):
        for sid in shocks:
            imp1, order = E.propagate(core.mats, core.idx, core.ids, [sid], frag=core.frag, nonlinear=nl,
                                      dt=core.dt)
            res[f'{sid}:{nl}'] = [_sha(imp1), len(order)]
    out['propagate'] = res
    fl = T._flow_impact(core)
    out['flow_sha'] = _sha({k: [list(v[0]), list(v[1]), list(v[2])] for k, v in sorted(fl.victims.items())})
    out['eff_weight'] = [E._eff_weight(4.0, 'wikidata'), E._eff_weight(None, 'curated', 0.3),
                         E._eff_weight(5.0, 'gleif', 0.5), E.fragility_cap(), E.bulk_weight_factor(),
                         E.SOLE_LINK_FLOOR, E.UNVERIFIED_CONF, sorted(E.BULK_SOURCES)]
    out['tensor'] = [T.DAMPING, T.MAX_HOPS, T.THRESHOLD, list(T.SUPPLIER_RELS), T.N_PEERS]
    return out


def _nrs():
    from core import world
    from core.hotviews import source
    from ontology import vocabulary as vocab
    data = source.load_snapshot()
    deg = vocab.flow_degree(data.links)
    vals = {n['id']: world.client_nrs(n, deg.get(n['id'], 0)) for n in data.nodes}
    extra = [world.client_nrs({'country': c, 'margin': m, 'growth': g, 'preipo': p}, d)
             for c in ('Taiwan', 'Japón', 'Estados Unidos', 'Perú', None)
             for m in (None, -2.0, 0.0, 0.1, 0.45) for g in ('🔴', '🟡', '') for p in (True, False)
             for d in (0, 3, 20)]
    return {'all_sha': _sha(vals), 'n': len(vals), 'sample': {k: vals[k] for k in sorted(vals)[:25]},
            'grid_sha': _sha(extra), 'grid_sum': sum(extra)}


def _committee():
    from research import committee as C
    claims = [
        {'id': 'c1', 'agent_type': 'fundamental', 'stance': 'positive', 'horizon': 'MEDIUM_TERM', 'confidence': 0.8},
        {'id': 'c2', 'agent_type': 'news', 'stance': 'negative', 'horizon': 'SHORT_TERM', 'confidence': 0.6},
        {'id': 'c3', 'agent_type': 'technical', 'stance': 'positive', 'horizon': 'LONG_TERM', 'confidence': 0.7},
        {'id': 'c4', 'agent_type': 'supply_chain', 'stance': 'positive', 'horizon': 'STRUCTURAL', 'confidence': 0.9},
        {'id': 'c5', 'agent_type': 'fundamental', 'stance': 'mixed', 'horizon': 'MEDIUM_TERM', 'confidence': 0.5},
        {'id': 'c6', 'agent_type': 'news', 'stance': 'positive', 'horizon': 'INTRADAY', 'confidence': 0.9},
    ]
    conv = C.conviction_by_horizon(claims, contradicted_ids=('c2',), reliab=lambda a: 0.6)
    out = {'conv_sha': _sha(conv)}
    dec = []
    for overall in (-80, -50, -35, -20, -5, 10, 35, 60):
        for has in (False, True):
            for cw, tw in ((0.0, None), (0.02, 0.05), (0.09, 0.05)):
                dec.append(C.decide(overall, has_position=has, current_w=cw, target_w=tw))
    dec.append(C.decide(50, insufficient=True))
    out['decide_sha'] = _sha(dec)
    sz = []
    mand = C.mandate_from({'mandate': {'risk_budget_pct': 2.5, 'max_position_pct': 12}})
    for d in ('BUY', 'ADD', 'TRIM', 'SELL', 'HOLD'):
        for vol in (8.0, 25.0, 60.0):
            for val in (True, False):
                sz.append(C.compute_sizing(d, vol, mand, equity=100000, current_value=3000, current_qty=10,
                                           price=300.0, buying_power=50000, validated=val))
    out['sizing_sha'] = _sha(sz)
    out['quorum'] = [C.quorum_check(p) for p in (['fundamental', 'news', 'technical'], ['news', 'technical',
                                                                                       'supply_chain'], [])]
    out['mandate_default'] = C.mandate_from({})
    out['targets'] = [C.effective_target_weight(v, C.mandate_from({}), validated=b) for v in (5, 20, 80)
                      for b in (True, False)]
    out['ttl'] = C._ttl_hours()
    return out


def _risk():
    from brokerage import risk as R
    base = {'client': {'status': 'active', 'mode': 'paper', 'live_enabled': False, 'connected': True,
                       'risk_profile': 'moderado', 'hwm_equity': 120000},
            'order': {'symbol': 'NVDA', 'side': 'buy', 'notional': 4000.0, 'order_type': 'market'},
            'account': {'equity': 100000, 'cash': 30000, 'buying_power': 60000}, 'positions': [
                {'symbol': 'NVDA', 'qty': 50, 'market_value': 9000, 'current_price': 180}],
            'price': 180.0, 'ref_price': 180.0, 'est_usd': 4000.0, 'daily_used_usd': 12000, 'market_open': False,
            'clock_source': 'alpaca'}
    cases = [base,
             {**base, 'client': {**base['client'], 'risk_profile': 'conservador'}},
             {**base, 'client': {**base['client'], 'risk_profile': 'agresivo'}, 'est_usd': 30000.0},
             {**base, 'order': {**base['order'], 'side': 'sell', 'qty': 60, 'notional': None}},
             {**base, 'order': {**base['order'], 'order_type': 'limit', 'limit_price': 205.0, 'qty': 5,
                                'notional': None}, 'est_usd': 1025.0},
             {**base, 'order': {**base['order'], 'symbol': 'BTC/USD'}, 'recent_duplicate': True}]
    os.environ.pop('BROKERAGE_TRADING_ENABLED', None)
    out = [[(c['name'], c['ok'], c.get('warn'), c['detail'], c.get('detail_en')) for c in R.run_checks(x)]
           for x in cases]
    lim = [R.effective_limits(p, {'max_order_usd': 999999}) for p in ('conservador', 'moderado', 'agresivo', 'x')]
    return {'checks_sha': _sha(out), 'limits': lim,
            'consts': [R.HARD_MAX_ORDER_USD, R.MIN_ORDER_USD, R.DUPLICATE_WINDOW_S, R.LIMIT_DEVIATION_PCT]}


def _numbers():
    from core import numbers as N
    grid = [N._tol(k, c, h, a) for k in ('money_big', 'price', 'pct', 'mult') for c in (0.5, 3.0, 181.2, 5.7e12)
            for h in (0.005, 0.05, 0.5) for a in (False, True)]
    texts = [('NVDA cotiza a 181,20 USD y vale 4,4 billones de dólares.', 'precio 181.2 cap 4.4e12'),
             ('El margen subió a 55 % y el P/E es 42x.', 'margin 55.8 pe 42.3'),
             ('Cerca de 190 dólares, alrededor de 182 USD.', 'price 182.4'),
             ('Más de 3 mil millones de dólares.', 'revenue 3.4e9'),
             ('La acción vale 233,95 USD.', 'price 181.2')]
    chk = [N.unsupported_in(t, e) for t, e in texts]
    return {'tol_sha': _sha(grid), 'tol_sum': sum(grid), 'check_sha': _sha(chk)}


def _policies():
    from core import decide
    from ontology import agents
    return {'safe_auto': sorted(agents.SAFE_AUTO), 'auto_min_conf': agents.AUTO_MIN_CONFIDENCE,
            'jev': [decide.MIN_CONF, decide.CONTROL_WAIT_S, list(decide.CONTROL_DEFAULT)]}


def compute():
    for k in ('FRAGILITY_CAP', 'IMPORT_BULK_WEIGHT_FACTOR', 'DECIDE_MIN_CONF', 'DECIDE_WAIT_S',
              'COMMITTEE_MEMO_TTL_HOURS'):
        os.environ.pop(k, None)
    return {'kernel': _kernel(), 'nrs': _nrs(), 'committee': _committee(), 'risk': _risk(), 'numbers': _numbers(),
            'policies': _policies()}


def _golden():
    with open(GOLDEN, encoding='utf-8') as fh:
        return json.load(fh)


def _norm(x):
    return json.loads(json.dumps(x, sort_keys=True, default=repr))


def test_paridad_kernel_impact_y_tensor():
    assert _norm(_kernel()) == _golden()['kernel']


def test_paridad_nrs_de_todos_los_nodos(monkeypatch):
    import core.live_fundamentals as lf
    monkeypatch.setattr(lf, 'live_margin', lambda *_a, **_k: None)   # sin márgenes en vivo de otras pruebas
    assert _norm(_nrs()) == _golden()['nrs']


def test_paridad_comite():
    assert _norm(_committee()) == _golden()['committee']


def test_paridad_controles_del_corretaje(monkeypatch):
    monkeypatch.delenv('BROKERAGE_TRADING_ENABLED', raising=False)
    assert _norm(_risk()) == _golden()['risk']


def test_paridad_guardian_de_cifras():
    assert _norm(_numbers()) == _golden()['numbers']


def test_paridad_politicas():
    assert _norm(_policies()) == _golden()['policies']


def test_los_valores_vienen_del_registro():
    """Las constantes de los módulos SON las del artefacto vigente (no una copia que pueda divergir)."""
    from brokerage import risk as R
    from core import decide, governance, world
    from matrix import engine as E
    from matrix import tensor as T
    from ontology import agents
    from research import committee as C
    kp = governance.section('kernel.params')
    assert E.SOLE_LINK_FLOOR == kp['sole_link_floor'] and E.fragility_cap() == kp['fragility_cap']
    assert E.DEFAULT_REL_WEIGHTS == kp['rel_weights'] and T.DAMPING == kp['damping']
    assert R.HARD_MAX_ORDER_USD == governance.param('policy.broker_risk', 'hard_max_order_usd')
    assert R.PROFILES == governance.param('policy.broker_risk', 'profiles')
    assert C.BUY_T == governance.param('policy.committee', 'buy_threshold')
    assert C.HZ_WEIGHTS == governance.param('policy.committee', 'hz_weights')
    assert agents.SAFE_AUTO == set(governance.param('policy.auto_apply', 'safe_auto'))
    assert decide.MIN_CONF == governance.param('policy.decide', 'min_conf')
    assert world._NRS_GEO == governance.param('nrs.formula', 'geo')


if __name__ == '__main__':
    if '--write' in sys.argv:
        os.makedirs(os.path.dirname(GOLDEN), exist_ok=True)
        data = _norm(compute())
        with open(GOLDEN, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1, sort_keys=True)
        print('dorado escrito:', GOLDEN)
    else:
        print(json.dumps(_norm(compute()), ensure_ascii=False, indent=1)[:3000])
