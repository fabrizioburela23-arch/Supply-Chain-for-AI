"""tests/gates_cases.py — generador de focos ALEATORIOS (con semilla) y accesorios de un solo defecto para las
pruebas de conformidad de las puertas (tests/test_gates_conformance.py) y de estado resultante.

Cada caso es (kind, entrada) → core/gates/focus.<kind>_triples(entrada). Todos los ids llevan el número de caso
como prefijo: varios casos pueden ir en UN grafo de datos para pySHACL sin mezclarse.
"""
import random
from datetime import datetime, timezone

KINDS = ('link', 'object', 'factor', 'action', 'decision', 'order', 'memo')
LIMITS = {'max_weight': 6.0, 'severity_scale': 10.0, 'high_conf_min': 0.5, 'min_trust': 2, 'max_member_coef': 1.0}


def _vocab():
    from core import decisions
    from ontology import vocabulary as vocab
    return (sorted(vocab.relation_types_all()), sorted(vocab.object_types()), tuple(vocab.flow_relation_types()),
            sorted(decisions.KINDS))


def _d(y, m=1, d=1):
    return datetime(y, m, d, tzinfo=timezone.utc)


def link_case(rng, n, rels, otypes, flow):
    a, b = f'c{n}_A', f'c{n}_B'
    src = a
    tgt = a if rng.random() < 0.12 else b
    vf = rng.choice([_d(2000), _d(2024, 5), _d(2026, 1), None])
    vt = rng.choice([None, None, _d(2025, 6), _d(1999)])
    inp = {'id': f'c{n}_L', 'source': src, 'target': tgt,
           'rel': rng.choice(rels + ['suministra_a', 'supply', 'fab', 'partner']) if rng.random() > 0.05 else None,
           'weight': rng.choice([None, 0, 2.5, 6, 6.0001, 7.5, -3, 'abc', True]),
           'confidence': rng.choice([None, 0, 0.3, 0.5, 0.49, 0.9, 1, 3, -0.1, 'alta']),
           'valid_from': vf, 'valid_to': vt,
           'rel_label': rng.choice(['', 'provee chips', 'Apple usa TSMC', 'USES the fab', 'causa daño', 'utiliza']),
           'evidenced_by': [f'c{n}_S'] if rng.random() < 0.4 else [],
           'dated': rng.random() < 0.3}
    endpoints = {}
    for oid in {src, tgt}:
        if rng.random() < 0.9:
            endpoints[oid] = {'type': rng.choice(otypes + ['Country', 'Policy', 'Company']), 'live': rng.random() < 0.85}
    inverses = []
    for k in range(rng.choice([0, 0, 1, 2])):
        inverses.append({'id': f'c{n}_R{k}', 'source': rng.choice([tgt, src]), 'target': rng.choice([src, tgt]),
                         'rel': rng.choice([inp['rel'] or 'supply', 'supply', 'fab', 'partner']),
                         'live': rng.random() < 0.7})
    sources = {f'c{n}_S': rng.choice([None, 1, 2, 3, 'alto'])} if inp['evidenced_by'] else {}
    sources = {k: v for k, v in sources.items() if v is not None}
    lim = dict(LIMITS, max_weight=rng.choice([6.0, 1.0]), high_conf_min=rng.choice([0.5, 0.8]))
    return {'link': inp, 'endpoints': endpoints, 'inverses': inverses, 'sources': sources, 'limits': lim,
            'flow_rels': flow}


def object_case(rng, n, otypes):
    t = rng.choice(otypes + ['Widget', 'Company']) if rng.random() > 0.05 else None
    props = {}
    for key, pool in (('margin', [None, 0.2, -1, -1.5, 1, 3, 'alto', 0.55]),
                      ('severity', [None, 5, 'alto', 2.5]), ('severity_crisis', [None, 9, 'muy alta'])):
        v = rng.choice(pool)
        if v is not None:
            props[key] = v
    return {'id': f'c{n}_O', 'type': t, 'prev_type': rng.choice([None, None, t, 'Company', 'Org']), 'props': props}


def factor_case(rng, n):
    props = {'severity': rng.choice([None, 0, 1, 5, 8, 10, 12, -1, 'alto']),
             'severity_crisis': rng.choice([None, 4, 9, 11, 'x']),
             'activo': rng.random() < 0.5, 'expired': rng.random() < 0.2}
    prev = None
    if rng.random() < 0.6:
        prev = {'severity': rng.choice([props['severity'], 1, 5, None, 'alto']), 'activo': rng.choice([props['activo'],
                                                                                                         not props['activo']])}
    members = [{'id': f'c{n}_M{k}', 'target': f'c{n}_T{k}', 'coef': rng.choice([0.5, 1, 1.0, 0, 1.5, -0.2, 0.05]),
                'live': rng.random() < 0.7} for k in range(rng.choice([0, 1, 2, 3]))]
    return {'f': {'id': f'c{n}_F', 'props': props, 'prev_props': prev, 'touches': rng.random() < 0.6,
                  'members': members}, 'limits': dict(LIMITS, severity_scale=rng.choice([10.0, 5.0]))}


def action_case(rng, n):
    from ontology.actions import ACTION_CATALOG
    at = rng.choice(sorted(ACTION_CATALOG) + ['Inventada'])
    pk = rng.choice([('human', 'pin'), ('human', 'none'), ('agent', 'agent_registry'), ('system', 'scheduler'),
                     ('external_ai', 'mcp_token'), ('system', 'none')])
    return {'id': f'c{n}_A', 'action_type': at, 'principal': {'id': f'p{n}', 'kind': pk[0], 'auth': pk[1]},
            'auto_apply': rng.random() < 0.4, 'confidence': rng.choice([None, 0.3, 0.55, 0.549, 0.9, 'x']),
            'nivel': rng.choice([None, 50, 100, 150, -5]), 'reason': rng.choice([None, '', 'porque sí']),
            'unknown_fields': rng.choice([[], [], ['peso'], ['peso', 'extra']]),
            'safe_auto': rng.choice([['AnotarObjeto', 'MarcarRiesgo', 'ProponerVinculo', 'IncorporarEmpresa',
                                      'CrearFactor'], ['AnotarObjeto', 'MarcarRiesgo'], []]),
            'auto_min_conf': rng.choice([0.55, 0.9])}


def decision_case(rng, n, kinds):
    quotes = []
    for k in range(rng.choice([0, 0, 1, 2])):
        quotes.append({'ticker': f'T{k}', 'as_of': rng.choice([None, '2026-10-12T14:00:00Z']),
                       'src': rng.choice([None, 'finnhub'])})
    return {'id': f'c{n}_D', 'kind': rng.choice(kinds + ['foo.bar', 'order.confirm', 'order.submit']),
            'status': rng.choice(['executed', 'rejected', 'recorded', None]),
            'principal_kind': rng.choice(['human', 'agent', 'system', 'robot', None]),
            'release_hash': rng.choice(['a' * 64, '0' * 64, 'abc', None]),
            'verdict': rng.choice([None, 'pass', 'warn', 'block']), 'quotes': quotes}


def order_case(rng, n):
    """Hechos de una orden (brokerage/risk.order_facts) con valores buenos, malos y de tipo equivocado."""
    side = rng.choice(['buy', 'sell', 'buy', 'hold', None])
    pick = rng.choice
    f = {'id': f'c{n}_O', 'symbol': pick(['NVDA', 'BTC/USD', 'NV DA', 'AAPL']), 'side': side,
         'order_type': pick(['market', 'limit']), 'trading_enabled': pick([True, True, False, None, 'on']),
         'account_mode': pick(['paper', 'live', 'paper', None]), 'client_status': pick(['active', 'paused', None]),
         'account_readable': pick([True, False, None]), 'symbol_valid': pick([True, True, False, None]),
         'asset_class': pick(['us_equity', 'crypto', None]),
         'allowed_asset_classes': pick([['us_equity'], ['us_equity', 'crypto'], []]),
         'restricted_symbols': pick([[], [], ['NVDA'], ['TSLA', 'AAPL']]),
         'allowed_symbols': pick([[], [], ['NVDA', 'AMD'], ['AAPL']]),
         'est_usd': pick([None, 0.5, 50, 500, 6000, 150000, 'x']), 'min_order_usd': pick([1, 1.0, None]),
         'max_order_usd': pick([None, 5000, 100000]), 'daily_after_usd': pick([None, 1000, 16000]),
         'max_daily_usd': pick([None, 15000]), 'needs_funds': pick([True, False, None]),
         'available_usd': pick([None, 100, 10000, 'abc']), 'position_pct_after': pick([None, 5, 20, 23.5]),
         'max_position_pct': pick([None, 20, 20.0]), 'drawdown_pct': pick([None, 0, 25.0]),
         'max_drawdown_pct': pick([None, 20]), 'short_sale': pick([None, True, False]),
         'duplicate_recent': pick([None, False, True]), 'unresolved': pick([None, False, True]),
         'ref_price_known': pick([None, True, False]), 'limit_dev_pct': pick([None, -12.0, -2, 0, 3, 15.5, 'x']),
         'max_limit_dev_pct': pick([None, 10]), 'min_limit_dev_pct': pick([None, -10]),
         'market_open': pick([None, True, False]), 'origin': pick(['ui', 'mcp', 'committee', 'agent', None]),
         'channel': pick(['ui', 'voice', 'crypto', None]), 'paper_auto_approved': pick([None, True, False]),
         'readback_sha': pick([None, 'a' * 64]), 'quote_age_s': pick([None, 2, 75]),
         'max_quote_age_s': pick([None, 60]), 'account_age_s': pick([None, 1, 45]),
         'max_account_age_s': pick([None, 30]), 'sector_weight_after': pick([None, 0.2, 0.55]),
         'max_sector_weight': pick([None, None, 0.4]), 'country_weight_after': pick([None, 0.3, 0.8]),
         'max_country_weight': pick([None, 0.6]), 'chain_exposure_after': pick([None, 0.1, 0.5]),
         'max_chain_exposure': pick([None, 0.3]), 'policy_changed': pick([None, False, True])}
    if rng.random() < 0.5:
        f.update(live_env_enabled=pick([True, False]), client_live_enabled=pick([True, False]),
                 ledger_chain_ok=pick([True, False, None]))
    return f


def memo_case(rng, n):
    """Hechos de un memo del comité (core/decision_sites.memo_facts): decisión, validación, tamaño, edad, quórum."""
    pick = rng.choice
    raw = pick([None, 3.0, 5.304, 12.0])
    mx = pick([None, 10.0, 5.0])
    validated = pick([True, False, None])
    full = min(raw, mx) if raw is not None and mx is not None else None
    target = pick([None, 0, 2.652, 5.0, 6.0, 11.0] + ([round(full / 2, 3), full] if full is not None else []))
    return {'id': f'c{n}_M', 'decision': pick(['BUY', 'ADD', 'HOLD', 'TRIM', 'SELL', 'AVOID', 'WAIT', None]),
            'quant_decision': pick(['BUY', 'HOLD', None]), 'decision_code': pick([None, None, 'INSUFFICIENT_DATA']),
            'validated': validated, 'sizing_unvalidated': pick([None, True, False]),
            'target_weight_pct': target, 'max_position_pct': mx,
            'max_unvalidated_weight_pct': (round(full * 0.5, 4) + 0.001) if (validated is False and full is not None)
            else pick([None, None, 1.0]),
            'age_hours': pick([None, 0, 1.5, 71.9, 72, 80]), 'ttl_hours': pick([None, 72, 24]),
            'quorum_ok': pick([None, True, False]), 'n_claims': pick([None, 0, 2, 5]),
            'ai_used': pick([True, False])}


def random_cases(seed, n):
    """[(kind, entrada)] — n casos repartidos entre los 7 focos."""
    rng = random.Random(seed)
    rels, otypes, flow, kinds = _vocab()
    out = []
    for i in range(n):
        k = KINDS[i % len(KINDS)]
        if k == 'link':
            out.append(('link', link_case(rng, i, rels, otypes, flow)))
        elif k == 'object':
            out.append(('object', object_case(rng, i, otypes)))
        elif k == 'factor':
            out.append(('factor', factor_case(rng, i)))
        elif k == 'action':
            out.append(('action', action_case(rng, i)))
        elif k == 'order':
            out.append(('order', order_case(rng, i)))
        elif k == 'memo':
            out.append(('memo', memo_case(rng, i)))
        else:
            out.append(('decision', decision_case(rng, i, kinds)))
    return out


def triples_of(kind, inp):
    from core.gates import focus as F
    if kind == 'link':
        return F.link_triples(inp['link'], inp['endpoints'], inp['inverses'], inp['sources'], inp['limits'],
                              inp['flow_rels'])
    if kind == 'object':
        return F.object_triples(inp)
    if kind == 'factor':
        return F.factor_triples(inp['f'], inp['limits'])
    if kind == 'action':
        return F.action_triples(inp)
    if kind == 'order':
        return F.order_triples(inp)
    if kind == 'memo':
        return F.memo_triples(inp)
    if kind == 'import':
        from ontology import company_import as CI
        return CI.import_triples(inp)
    return F.decision_triples(inp)


# ── un solo defecto por regla: (regla esperada, kind, entrada) ───────────────
def single_defect_cases():
    flow = ('supply', 'fab', 'cloud', 'license', 'ppa', 'owns', 'deploy')
    good_eps = {'X_A': {'type': 'Company', 'live': True}, 'X_B': {'type': 'Company', 'live': True}}
    base = {'id': 'X_L', 'source': 'X_A', 'target': 'X_B', 'rel': 'supply', 'weight': 3, 'confidence': None,
            'valid_from': _d(2000), 'valid_to': None, 'rel_label': 'provee', 'evidenced_by': [], 'dated': False}

    def L(rule, link=None, eps=None, inv=(), sources=None):
        return (rule, 'link', {'link': dict(base, **(link or {})), 'endpoints': eps if eps is not None else good_eps,
                               'inverses': list(inv), 'sources': sources or {}, 'limits': LIMITS, 'flow_rels': flow})
    cases = [
        L(None),
        L('khr:link.rel_in_vocab', {'rel': 'suministra_a'}),
        L('khr:link.no_self_loop', {'target': 'X_A'}, {'X_A': {'type': 'Company', 'live': True}}),
        L('khr:link.endpoints_live', eps={'X_A': {'type': 'Company', 'live': True}, 'X_B': {'type': 'Company',
                                                                                          'live': False}}),
        L('khr:link.weight_range', {'weight': 7.5}),
        L('khr:link.confidence_range', {'confidence': 3, 'rel': 'partner'}),
        L('khr:link.valid_interval', {'valid_to': _d(1990)}),
        L('khr:link.flow_supplier_type', eps={'X_A': {'type': 'Country', 'live': True}, 'X_B': {'type': 'Company',
                                                                                              'live': True}}),
        L('khr:link.inverse_flow_live', inv=[{'id': 'X_R', 'source': 'X_B', 'target': 'X_A', 'rel': 'supply',
                                              'live': True}]),
        L('khr:link.high_conf_trusted_source', {'confidence': 0.9}),
        L('khr:link.direction_text_suspect', {'rel_label': 'Apple usa chips de TSMC'}),
        L('khr:link.dated_fact_has_source', {'dated': True}),
        ('khr:object.type_in_vocab', 'object', {'id': 'X_O', 'type': 'Widget', 'prev_type': None, 'props': {}}),
        ('khr:object.type_immutable', 'object', {'id': 'X_O', 'type': 'Company', 'prev_type': 'Org', 'props': {}}),
        ('khr:object.margin_range', 'object', {'id': 'X_O', 'type': 'Company', 'prev_type': None,
                                               'props': {'margin': 3}}),
        ('khr:object.numeric_props', 'object', {'id': 'X_O', 'type': 'Factor', 'prev_type': 'Factor',
                                                'props': {'severity': 'alto'}}),
    ]
    fbase = {'id': 'X_F', 'props': {'severity': 1, 'severity_crisis': 8, 'activo': False, 'expired': False},
             'prev_props': {'severity': 1, 'activo': False}, 'touches': False,
             'members': [{'id': 'X_M', 'target': 'X_T', 'coef': 0.5, 'live': True}]}

    def Fc(rule, props=None, prev=None, touches=False, members=None):
        f = dict(fbase, props=dict(fbase['props'], **(props or {})), touches=touches)
        if prev is not None:
            f['prev_props'] = prev
        if members is not None:
            f['members'] = members
        return (rule, 'factor', {'f': f, 'limits': LIMITS})
    cases += [
        Fc(None),
        Fc('khr:factor.severity_scale', {'severity': 12}),
        Fc('khr:factor.not_retired', {'expired': True, 'activo': True}, prev={'severity': 1, 'activo': True}),
        Fc('khr:factor.coef_range', members=[{'id': 'X_M', 'target': 'X_T', 'coef': 0, 'live': True}]),
        Fc('khr:factor.has_live_members', members=[{'id': 'X_M', 'target': 'X_T', 'coef': 0.5, 'live': False}]),
        Fc('khr:factor.noop', touches=True),
    ]
    abase = {'id': 'X_A', 'action_type': 'AnotarObjeto', 'principal': {'id': 'op:fabrizio', 'kind': 'human',
                                                                       'auth': 'pin'},
             'auto_apply': False, 'confidence': None, 'nivel': None, 'reason': None, 'unknown_fields': [],
             'safe_auto': ['AnotarObjeto', 'MarcarRiesgo'], 'auto_min_conf': 0.55}

    def A(rule, **kw):
        return (rule, 'action', dict(abase, **kw))
    cases += [
        A(None),
        A('khr:action.principal_authenticated', principal={'id': 'ui:anon', 'kind': 'human', 'auth': 'none'}),
        A('khr:action.no_unknown_fields', unknown_fields=['peso']),
        A('khr:action.risk_level_range', action_type='MarcarRiesgo', nivel=150),
        A('khr:action.auto_apply_allowed', auto_apply=True, confidence=0.3),
        A('khr:action.agent_needs_human', action_type='CrearTesis',
          principal={'id': 'agent:x', 'kind': 'agent', 'auth': 'agent_registry'}),
        A('khr:action.retraction_has_reason', action_type='RetractarVinculo', reason=''),
    ]
    dbase = {'id': 'X_D', 'kind': 'ontology.action', 'status': 'executed', 'principal_kind': 'human',
             'release_hash': 'b' * 64, 'verdict': None, 'quotes': []}

    def D(rule, **kw):
        return (rule, 'decision', dict(dbase, **kw))
    cases += [
        D(None),
        D('khr:decision.kind_in_vocab', kind='foo.bar'),
        D('khr:decision.principal_typed', principal_kind='robot'),
        D('khr:decision.release_present', release_hash='0' * 64),
        D('khr:decision.quotes_have_asof_src', quotes=[{'ticker': 'NVDA', 'as_of': None, 'src': 'finnhub'}]),
        D('khr:decision.money_executed_not_blocked', kind='order.confirm', verdict='block'),
    ]
    # orden limpia (compra en papel, todo dentro de los límites) y un defecto por regla
    obase = {'id': 'X_O', 'symbol': 'NVDA', 'side': 'buy', 'order_type': 'market', 'trading_enabled': True,
             'account_mode': 'paper', 'client_status': 'active', 'account_readable': True, 'symbol_valid': True,
             'asset_class': 'us_equity', 'allowed_asset_classes': ['us_equity', 'crypto'], 'restricted_symbols': [],
             'allowed_symbols': [], 'est_usd': 500, 'min_order_usd': 1, 'max_order_usd': 5000,
             'daily_after_usd': 500, 'max_daily_usd': 15000, 'needs_funds': True, 'available_usd': 10000,
             'position_pct_after': 5, 'max_position_pct': 20, 'drawdown_pct': 0, 'max_drawdown_pct': 20,
             'duplicate_recent': False, 'unresolved': False, 'market_open': True, 'origin': 'ui', 'channel': 'ui',
             'quote_age_s': 1, 'max_quote_age_s': 60, 'account_age_s': 1, 'max_account_age_s': 30,
             'sector_weight_after': 0.2, 'max_sector_weight': 0.4, 'country_weight_after': 0.3,
             'max_country_weight': 0.6, 'chain_exposure_after': 0.1, 'max_chain_exposure': 0.3,
             'policy_changed': False}

    def O(rule, **kw):
        return (rule, 'order', dict(obase, **kw))
    sell = {'side': 'sell', 'needs_funds': None, 'available_usd': None, 'position_pct_after': None,
            'max_position_pct': None, 'daily_after_usd': None, 'short_sale': False}
    lim = {'order_type': 'limit', 'ref_price_known': True, 'max_limit_dev_pct': 10, 'min_limit_dev_pct': -10}
    cases += [
        O(None),
        O('khr:order.kill_switch', trading_enabled=False),
        O('khr:order.ledger_chain', account_mode='live', live_env_enabled=True, client_live_enabled=True,
          ledger_chain_ok=False),
        O('khr:order.mode_live_enabled', account_mode='live', live_env_enabled=True, client_live_enabled=False,
          ledger_chain_ok=True),
        O('khr:order.client_active', client_status='paused'),
        O('khr:order.account_readable', account_readable=False),
        O('khr:order.symbol_tradable', symbol_valid=False, asset_class=None),
        O('khr:order.asset_class_allowed', symbol='BTC/USD', asset_class='crypto', allowed_asset_classes=['us_equity'],
          market_open=None),
        O('khr:order.restricted', restricted_symbols=['NVDA']),
        O('khr:order.not_allowed', allowed_symbols=['AAPL', 'MSFT']),
        O('khr:order.price_known', est_usd=None, daily_after_usd=None, available_usd=10000, needs_funds=None,
          position_pct_after=None, max_position_pct=None, side='sell', short_sale=False),
        O('khr:order.min_order_usd', est_usd=0.5, daily_after_usd=0.5),
        O('khr:order.max_order_usd', est_usd=6000, daily_after_usd=6000),
        O('khr:order.daily_cap', daily_after_usd=16000),
        O('khr:order.buying_power', available_usd=100),
        O('khr:order.position_pct_after', position_pct_after=23.5),
        O('khr:order.drawdown_stop', drawdown_pct=25.0),
        O('khr:order.no_short', **dict(sell, short_sale=True)),
        O('khr:order.duplicate_window', duplicate_recent=True),
        O('khr:order.unresolved', unresolved=True),
        O('khr:order.limit_deviation', **dict(lim, limit_dev_pct=15.5)),
        O('khr:order.limit_passive', **dict(lim, limit_dev_pct=-15.5)),
        O('khr:order.limit_reference', **dict(lim, ref_price_known=False, max_limit_dev_pct=None,
                                              min_limit_dev_pct=None)),
        O('khr:order.market_hours', market_open=False),
        O('khr:order.sector_pct_after', sector_weight_after=0.55),
        O('khr:order.country_pct_after', country_weight_after=0.8),
        O('khr:order.chain_exposure_after', chain_exposure_after=0.5),
        O('khr:order.quote_fresh', quote_age_s=75),
        O('khr:order.account_fresh', account_age_s=45),
        O('khr:order.ai_origin_needs_human', origin='mcp'),
        O('khr:order.voice_readback', channel='voice'),
        O('khr:order.policy_changed_since_preview', policy_changed=True),
    ]
    # memo del comité limpio (BUY validado, dentro del mandato, recién hecho) y un defecto por regla (G5, paso 18)
    mbase = {'id': 'X_M', 'decision': 'BUY', 'quant_decision': 'BUY', 'decision_code': None, 'validated': True,
             'sizing_unvalidated': False, 'target_weight_pct': 5.304, 'max_position_pct': 10.0,
             'max_unvalidated_weight_pct': None, 'age_hours': 0.1, 'ttl_hours': 72, 'quorum_ok': True,
             'n_claims': 6, 'ai_used': True}
    unv = {'validated': False, 'sizing_unvalidated': True, 'target_weight_pct': 2.652,
           'max_unvalidated_weight_pct': 2.653}

    def M(rule, **kw):
        return (rule, 'memo', dict(mbase, **kw))
    cases += [
        M(None),
        M(None, **unv),
        M(None, decision='HOLD', decision_code='INSUFFICIENT_DATA', quorum_ok=False, ai_used=False),
        M('khr:memo.manifest_complete', decision='WAIT'),
        M('khr:memo.size_le_mandate', target_weight_pct=12.5),
        M('khr:memo.not_expired', age_hours=80),
        M('khr:memo.unvalidated_half', **dict(unv, target_weight_pct=5.304, max_position_pct=10.0)),
        M('khr:memo.unvalidated_label', **dict(unv, sizing_unvalidated=False)),
        M('khr:memo.quorum', quorum_ok=False, ai_used=False),
        M('khr:memo.quorum_no_ai', decision='HOLD', decision_code='INSUFFICIENT_DATA', quorum_ok=False),
    ]
    # E2.5 (lote K): las 14 reglas de importación de empresas (company.ttl)
    from tests.test_import_shapes import import_single_defect_cases
    cases += import_single_defect_cases()
    return cases
