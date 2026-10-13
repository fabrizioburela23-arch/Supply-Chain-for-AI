"""tests/test_gates_orders_parity.py — INFRA_OPERATIVA paso 17: la puerta de ÓRDENES (governance/shapes/order.ttl,
compilada en core/gates) dice EXACTAMENTE lo mismo que brokerage/risk.run_checks, control por control.

  · ≥ 3.000 contextos aleatorios (semilla fija; papel/real, compra/venta, mercado/límite, cripto, mandatos, cuentas
    ilegibles, interruptores, duplicados, caídas desde el máximo, límites del cliente, política «house_today») →
    {(control, block|warn)} de run_checks == {(control, severidad declarada)} de la puerta: 0 diferencias;
  · cada control de run_checks tiene su IRI (brokerage/risk.CHECK_RULES) y la puerta compila todas;
  · las reglas NUEVAS (sector, país, cadena, frescura, origen IA, voz, política cambiada) solo aplican con su literal;
  · la puerta en el servicio corre en SOMBRA: nunca bloquea (el veredicto que rige es el de run_checks).
Sin red, sin base: es la misma función de hechos (risk.order_facts) que usa el corretaje en vivo.
"""
import os
import random
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

N = int(os.getenv('ORDER_PARITY_N') or 3000)


@pytest.fixture(scope='module')
def comp():
    from core.gates import engine
    return engine.compile_ir(engine.read_ir_file())


def _rand_ctx(rng):
    from brokerage import risk
    mode = rng.choice(['paper', 'paper', 'live'])
    side = rng.choice(['buy', 'sell'])
    otype = rng.choice(['market', 'market', 'limit'])
    sym = rng.choice(['NVDA', 'AAPL', 'BTC/USD', 'NV DA', 'TSLA', 'ETH/USD', 'BRK.B'])
    est = rng.choice([None, 0.5, 50.0, 500.0, 999.0, 4999.0, 5000.0, 6000.0, 14000.0, 26000.0, 120000.0])
    qty = rng.choice([None, 1.0, 5.0, 20.0])
    lp = rng.choice([50.0, 89.0, 95.0, 100.0, 105.0, 111.0, 150.0]) if otype == 'limit' else None
    ref = rng.choice([None, 100.0, 100.0])
    profile = rng.choice(['conservador', 'moderado', 'agresivo'])
    mandate = rng.choice([{}, {}, {'restricted_symbols': ['TSLA']}, {'allowed_symbols': ['NVDA', 'AAPL']},
                          {'allowed_asset_classes': ['us_equity']}, {'allow_margin': True}])
    limits = rng.choice([{}, {}, {'max_order_usd': 700}, {'max_daily_usd': 1000}, {'max_position_pct': 5}])
    acct = rng.choice([None, {'equity': 10000.0, 'cash': 10000.0, 'buying_power': 20000.0},
                       {'equity': 10000.0, 'cash': 100.0, 'buying_power': 100.0},
                       {'equity': 0.0, 'cash': 0.0, 'buying_power': 0.0},
                       {'equity': 8000.0, 'cash': 5000.0, 'buying_power': 16000.0,
                        'non_marginable_buying_power': 3000.0}])
    pos = rng.choice([[], [], [{'symbol': sym.replace('/', ''), 'qty': 10.0, 'market_value': 1000.0}],
                      [{'symbol': sym, 'qty': 2.0, 'market_value': 200.0}],
                      [{'symbol': 'AMD', 'qty': 3.0, 'market_value': 2000.0}]])
    ctx = {'client': {'status': rng.choice(['active', 'active', 'paused']), 'mode': mode,
                      'live_enabled': rng.choice([True, False]), 'connected': rng.choice([True, True, False]),
                      'risk_profile': profile, 'risk_limits': limits, 'mandate': mandate,
                      'hwm_equity': rng.choice([None, 10000.0, 20000.0, 9000.0])},
           'order': {'symbol': sym, 'side': side, 'notional': est if qty is None else None,
                     'qty': qty, 'order_type': otype, 'limit_price': lp},
           'account': acct, 'account_error': rng.choice([None, None, None, 'Alpaca HTTP 401']),
           'positions': pos, 'price': ref, 'ref_price': ref, 'est_usd': est,
           'daily_used_usd': rng.choice([0.0, 0.0, 14800.0, 900.0]),
           'recent_duplicate': rng.random() < 0.15, 'unresolved_order': rng.random() < 0.1,
           'market_open': rng.choice([True, False, None]), 'clock_source': rng.choice(['alpaca', 'approx'])}
    if mode == 'live':
        ctx['ledger_chain'] = (rng.choice([True, True, False]), 'x', 'x')
    if rng.random() < 0.35:
        # política de la casa SIN la sombra: la puerta mide lo DECLARADO (la sombra se aplica después)
        # (house_reduce = salidas de la casa: CLOSE y stop-loss, sin el tope por orden si solo reducen)
        ctx['policy'] = dict(risk.check_policy(rng.choice(['house_today', 'house_reduce'])), shadow=())
    return ctx


def _expected(checks):
    out = set()
    for c in checks:
        if not c['ok'] and c.get('severity', 'block') == 'block':
            out.add((c['name'], 'block'))
        elif c.get('warn'):
            out.add((c['name'], 'warn'))
    return out


def _got(comp, facts):
    from brokerage import risk
    from core.gates import engine
    from core.gates import focus as F
    inv = {r: name for name, rules in risk.CHECK_RULES.items() for r in rules}
    sev = {F.SH + 'Violation': 'block', F.SH + 'Warning': 'warn', F.KHS + 'RequiresApproval': 'approval'}
    t, _f = F.order_triples(facts)
    out = set()
    for _this, _k, spec, _v, _l in engine.run(comp, t):
        name = inv.get(spec['rule'])
        assert name is not None, f'regla de orden sin control de run_checks: {spec["rule"]}'
        out.add((name, sev[F.expand(spec['severity'])]))
    return out


def test_cada_control_tiene_su_regla(comp):
    from brokerage import risk
    rules = {r for rs in risk.CHECK_RULES.values() for r in rs}
    assert rules <= comp.rules, sorted(rules - comp.rules)
    order_rules = {r for r in comp.rules if r.startswith('khr:order.')}
    new = order_rules - rules
    assert new == {'khr:order.sector_pct_after', 'khr:order.country_pct_after', 'khr:order.chain_exposure_after',
                   'khr:order.quote_fresh', 'khr:order.account_fresh', 'khr:order.ai_origin_needs_human',
                   'khr:order.voice_readback', 'khr:order.policy_changed_since_preview'}, sorted(new)
    assert len(order_rules) == 31


def test_paridad_run_checks_vs_puerta(comp, monkeypatch):
    from brokerage import risk
    rng = random.Random(20261013)
    diffs, seen = [], set()
    for i in range(N):
        monkeypatch.setenv('BROKERAGE_TRADING_ENABLED', rng.choice(['on', 'on', 'on', 'off']))
        monkeypatch.setenv('BROKERAGE_LIVE_ENABLED', rng.choice(['on', 'off']))
        ctx = _rand_ctx(rng)
        want = _expected(risk.run_checks(ctx))
        got = _got(comp, risk.order_facts(ctx))
        seen |= {n for n, _s in want}
        if want != got:
            diffs.append((i, sorted(want ^ got)))
    assert diffs == [], diffs[:5]
    assert seen >= set(risk.CHECK_RULES), sorted(set(risk.CHECK_RULES) - seen)     # el generador ejercita TODO


def test_reglas_nuevas_solo_con_su_literal(comp):
    from brokerage import risk
    from core.gates import engine
    from core.gates import focus as F
    ctx = {'client': {'status': 'active', 'mode': 'paper', 'connected': True, 'risk_profile': 'moderado',
                      'risk_limits': {}, 'mandate': {}},
           'order': {'symbol': 'NVDA', 'side': 'buy', 'notional': 500.0, 'order_type': 'market'},
           'account': {'equity': 10000.0, 'cash': 10000.0, 'buying_power': 10000.0}, 'positions': [],
           'price': 100.0, 'ref_price': 100.0, 'est_usd': 500.0, 'market_open': True}

    def rules(extra):
        t, _f = F.order_triples(risk.order_facts(ctx, extra))
        return {s['rule'] for _x, _k, s, _v, _l in engine.run(comp, t)}
    base = {'sector_weight_after': 0.55, 'country_weight_after': 0.9, 'chain_exposure_after': 0.5,
            'quote_age_s': 120, 'account_age_s': 90, 'origin': 'mcp', 'channel': 'voice', 'policy_changed': True}
    got = rules(base)
    assert got == {'khr:order.ai_origin_needs_human', 'khr:order.voice_readback',
                   'khr:order.policy_changed_since_preview'}, got        # sin límites: sector/país/cadena/frescura no
    got = rules(dict(base, max_sector_weight=0.4, max_country_weight=0.6, max_chain_exposure=0.3,
                     max_quote_age_s=60, max_account_age_s=30, readback_sha='a' * 64, paper_auto_approved=True,
                     policy_changed=False))
    assert got == {'khr:order.sector_pct_after', 'khr:order.country_pct_after', 'khr:order.chain_exposure_after',
                   'khr:order.quote_fresh', 'khr:order.account_fresh'}, got     # papel + auto-aprobación: sin humano
    assert 'khr:order.ai_origin_needs_human' not in rules({'origin': 'agent', 'paper_auto_approved': True})
    assert 'khr:order.ai_origin_needs_human' in rules({'origin': 'committee', 'paper_auto_approved': False})


def test_la_puerta_corre_en_sombra(monkeypatch):
    """En el servicio la puerta solo AVISA (paso 17): todo resultado efectivo es 'warn'/'info', nunca 'block'."""
    from brokerage import risk, service
    from core.gates import report as gr

    class Ctx:
        def __init__(self):
            self.reports, self.durability, self.extra = [], 'sync', {}

        def gate(self, rep):
            self.reports.append(rep)

        def blob(self, *a, **k):
            return 'x'
    monkeypatch.setenv('BROKERAGE_TRADING_ENABLED', 'off')
    ctx = {'client': {'status': 'paused', 'mode': 'paper', 'connected': False, 'risk_profile': 'moderado',
                      'risk_limits': {}, 'mandate': {}},
           'order': {'symbol': 'NVDA', 'side': 'buy', 'notional': 500.0, 'order_type': 'market'},
           'account': None, 'positions': [], 'price': None, 'est_usd': None}
    ev = {'rc': ctx, 'checks': risk.run_checks(ctx), 'read_at': None, 'account': None, 'positions': []}
    c = Ctx()
    rep = service.order_gate(service.BrokerClient(id='x', mode='paper'), {'symbol': 'NVDA', 'side': 'buy'}, ev,
                             order_id='o1', source='mcp', channel='voice', ctx=c)
    assert rep is not None and rep['mode'] == 'shadow' and rep['n_results'] >= 4
    assert {r['effective'] for r in rep['results']} <= {'warn', 'info'} and rep['outcome'] == 'warn'
    assert c.reports and c.reports[0]['outcome'] == 'warn'
    assert gr.to_ctx_report(rep)['violations'][0]['value']['gate'] == 'order.pre_trade'
