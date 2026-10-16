"""«IA concreta» (2026-10-16): «optimiza mi cartera» → PLAN de 3-5 movimientos (core/portfolio_advisor.plan) que el
chat pide con plan_portfolio; las posiciones y el perfil los pone el SERVIDOR (nunca el modelo). Información, no
consejo: sin órdenes."""
from datetime import date

from core import portfolio_advisor as pa


def _risk(positions, horizon=10, max_positions=60):
    vals = {'NVDA': 6000.0, 'AMD': 2000.0, 'TSM': 1500.0, 'ASML': 500.0}
    vols = {'NVDA': 50.0, 'AMD': 55.0, 'TSM': 35.0, 'ASML': 30.0}
    syms = [p['symbol'] for p in positions]
    tot = sum(vals[s] for s in syms)
    rc = {'NVDA': 70.0, 'AMD': 18.0, 'TSM': 9.0, 'ASML': 3.0}
    corr = {('NVDA', 'AMD'): 0.85}
    mat = [[1.0 if a == b else corr.get((a, b), corr.get((b, a), 0.4)) for b in syms] for a in syms]
    return {'ok': True, 'portfolio_value_usd': tot, 'vol_ann_pct': 38.0, 'max_drawdown_pct': -30.0,
            'var95': {'hist_1d_pct': 3.1, 'hist_1d_usd': 310.0}, 'as_of': '2026-10-16T00:00:00Z', 'source': 'test',
            'positions': [{'symbol': s, 'value_usd': vals[s], 'vol_ann_pct': vols[s], 'risk_contrib_pct': rc[s]}
                          for s in syms],
            'correlation': {'symbols': syms, 'matrix': mat}}


def _board():
    return {}, []


def _analysis(lang='es', risk='moderado'):
    pos = [{'symbol': s, 'shares': 1} for s in ('NVDA', 'AMD', 'TSM', 'ASML')]
    return pa.analyze(pos, profile={'risk': risk}, lang=lang, risk_fn=_risk, board_fn=_board)


def test_plan_tiene_3_a_5_movimientos_concretos():
    a = _analysis()
    assert a['ok'] and a['correlation']['symbols']
    p = pa.plan(a, today=date(2026, 10, 16))
    assert p['ok'] and pa.PLAN_MIN <= len(p['moves']) <= pa.PLAN_MAX
    first = p['moves'][0]
    assert first['symbol'] == 'NVDA' and first['verb'] == 'sell' and first['amount_usd'] > 0
    assert first['from_pct'] == 60.0 and first['to_pct'] == 20.0 and first['why']
    assert [m['n'] for m in p['moves']] == list(range(1, len(p['moves']) + 1))
    assert all(m['verb'] in ('buy', 'sell', 'hold') for m in p['moves'])
    # antes → después: baja la concentración y el riesgo estimado
    assert p['before']['largest'] == 'NVDA' and p['after']['largest_pct'] < p['before']['largest_pct']
    assert p['after']['vol_ann_pct'] < p['before']['vol_ann_pct']
    assert p['totals']['sell_usd'] >= 4000 and p['totals']['cash_after_usd'] >= 0
    assert p['review']['on'] == '2026-10-23' and p['review']['in_days'] == 7
    assert p['watch'] and 'NVDA' in ' '.join(p['watch']) or 'Nvidia' in ' '.join(p['watch'])
    assert p['is_advice'] is False and p['orders'] is None and 'no consejo' in p['notice']


def test_plan_en_ingles_y_completa_con_mantener():
    a = _analysis(lang='en', risk='agresivo')
    p = pa.plan(a)
    assert p['lang'] == 'en' and 'not advice' in p['notice']
    assert len(p['moves']) >= pa.PLAN_MIN
    holds = [m for m in p['moves'] if m['verb'] == 'hold']
    assert all(m['amount_usd'] == 0 and m['action'] == 'Hold' for m in holds)


def test_chat_pone_posiciones_y_perfil_no_el_modelo():
    from core import khipu_chat as kc
    ctx = {'portfolio': [{'symbol': 'NVDA', 'shares': 2.0, 'usd': 300.0}], 'investor_risk': 'conservador'}
    out = kc._server_args('plan_portfolio', {'positions': [{'symbol': 'FAKE', 'shares': 9e9}]}, ctx)
    assert out['positions'] == [{'symbol': 'NVDA', 'shares': 2.0, 'usd': 300.0}] and out['risk'] == 'conservador'
    assert 'plan_portfolio' in kc._EXTRA
    ok, res = kc.execute_tool('plan_portfolio', {'positions': []})
    assert not ok and 'no listed positions' in res['error']


def test_chat_valida_perfil_del_contexto():
    from core import khipu_chat as kc
    import inspect
    src = inspect.getsource(kc)
    assert "ctx_raw.get('investor_risk') in ('conservador', 'moderado', 'agresivo')" in src
    assert 'plan_portfolio() SIN argumentos' in src
