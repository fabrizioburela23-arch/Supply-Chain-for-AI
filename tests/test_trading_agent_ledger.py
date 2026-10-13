"""tests/test_trading_agent_ledger.py — INFRA_OPERATIVA paso 16 (BRECHAS G5-10, MAP D #12, #14): el agente de trading
del servidor por EL camino único y con memoria.

  · cada señal que no es «mantener» queda en el libro como trade.agent_signal ANTES de actuar (precio que vio, tono,
    confianza, razón y modelo de la IA, configuración): 'executed' si mandó orden (su hija es la order.preview),
    'noop' si decidió no enviarla, 'recorded' si es solo consejo (modo manual);
  · sus órdenes salen por brokerage.service.house_order(source='agent'): mismos controles, client_order_id
    kh-agent-…, auditoría, decisiones; en PAPEL no espera a nadie, con dinero real esperaría aprobación humana;
  · BRECHAS #14 (por defecto): su configuración se guarda (policy.change) y tras un despliegue queda APAGADO con un
    aviso bilingüe visible, sin perder la configuración;
  · el sondeo de ejecuciones deja broker_fills (append-only) + decision_outcomes (fill, order_status) sin duplicar.
Sin red (bróker falso en la capa HTTP). Nunca una orden real.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

import requests  # noqa: E402

import server  # noqa: E402
from tests.test_order_single_path import HTTPAlpaca  # noqa: E402

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
PIN = '4321-strong-pin'
PAPER = 'https://paper-api.alpaca.markets'


@pytest.fixture(scope='module')
def db():
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    import brokerage.models  # noqa: F401
    import research.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def alpaca(monkeypatch, db):
    fake = HTTPAlpaca()
    for name in ('request', 'get', 'post', 'delete'):
        monkeypatch.setattr(requests, name, getattr(fake, name))
    for k, v in (('ALPACA_KEY', 'PKFAKEKEY0001'), ('ALPACA_SECRET', 'FAKE-SECRET-123'), ('ALPACA_BASE', PAPER)):
        monkeypatch.setattr(server, k, v)
        monkeypatch.setenv(k, v)
    monkeypatch.setenv('TRADE_PIN', PIN)
    for k in ('BROKERAGE_TRADING_ENABLED', 'BROKERAGE_LIVE_ENABLED', 'RAILWAY_ENVIRONMENT'):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(server, 'FINNHUB', 'fh')
    monkeypatch.setattr(server, '_fetch_quote_raw', lambda t, timeout=8: ({'c': 100.0, 'pc': 98.0}, None))
    from core import http as core_http
    from core import pin as core_pin
    core_pin._reset_for_tests()
    monkeypatch.setattr(core_http, '_rate_limit', lambda *a, **k: True)
    server._TRADABLE_CACHE.clear()
    return fake


@pytest.fixture
def agent(monkeypatch, alpaca):
    for k, v in (('running', True), ('mode', 'auto'), ('universe', ['AMD']), ('log', []), ('pending_close', {}),
                 ('daily_pnl_pct', 0.0), ('min_confidence', 65), ('max_orders_per_cycle', 3), ('max_pos_pct', 5.0),
                 ('stop_loss_pct', 3.0), ('interval_min', 15), ('max_daily_loss_pct', 2.0), ('thread', None),
                 ('status', 'stopped')):
        monkeypatch.setitem(server._AGENT, k, v)
    monkeypatch.setattr(server._trading_agent, '_agent_analyze', lambda *a, **k: {
        'action': 'buy', 'confidence': 91, 'reason': 'demanda de IA', 'size_pct': 2, '_model': 'claude-haiku-4-5'})
    return server._AGENT


def _q(sql, **kw):
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        return [dict(r._mapping) for r in s.execute(text(sql), kw)]


def _signals(symbol):
    return _q("SELECT id, status, parent_id, principal_id, output, model, manifest FROM decisions "
              "WHERE kind = 'trade.agent_signal' AND subject->>'symbol' = :s ORDER BY seq", s=symbol)


def test_signal_is_written_before_the_order_and_parents_it(agent, alpaca):
    server._agent_run_cycle()
    e = [x for x in agent['log'] if x.get('ticker') == 'AMD'][-1]
    assert e['executed'] is True, e
    sig = _signals('AMD')[-1]
    assert sig['status'] == 'executed' and sig['principal_id'] == 'system:trading_agent'
    assert sig['output']['confidence'] == 91 and sig['output']['reason'] == 'demanda de IA'
    assert sig['model']['model'] == 'claude-haiku-4-5' and sig['manifest']['quotes'][0]['px'] == 100.0
    pv = _q("SELECT id, kind, status, principal_id FROM decisions WHERE parent_id = :p", p=sig['id'])
    assert len(pv) == 1 and pv[0]['kind'] == 'order.preview' and pv[0]['principal_id'] == 'system:trading_agent'
    row = _q("SELECT id, source, client_order_id, status, meta FROM broker_orders WHERE meta->>'preview_decision_id'"
             " = :d", d=str(pv[0]['id']))[0]
    assert row['source'] == 'agent' and row['client_order_id'].startswith('kh-agent-') and row['status'] == 'submitted'
    assert row['meta']['channel'] == 'agent' and row['meta']['checks_mode'] == 'house_today'
    sub = _q("SELECT status, parent_id FROM decisions WHERE id = CAST(:i AS uuid)", i=row['meta']['submit_decision_id'])
    assert sub[0]['status'] == 'executed'
    assert alpaca.posts()[-1][3]['client_order_id'] == row['client_order_id']


def test_manual_mode_is_advice_only(agent, alpaca, monkeypatch):
    monkeypatch.setitem(agent, 'mode', 'manual')
    monkeypatch.setitem(agent, 'universe', ['INTC'])
    server._agent_run_cycle()
    assert not alpaca.posts()
    sig = _signals('INTC')[-1]
    assert sig['status'] == 'recorded' and sig['output']['executed'] is False


def test_skipped_order_is_a_noop_signal(agent, alpaca, monkeypatch):
    monkeypatch.setitem(agent, 'universe', ['MU'])
    monkeypatch.setattr(server._trading_agent, '_agent_analyze', lambda *a, **k: {'action': 'sell', 'confidence': 95,
                                                                    'reason': 'caro', 'size_pct': 2})
    server._agent_run_cycle()                      # vender sin tenencia: el agente no abre cortos
    assert not alpaca.posts()
    sig = _signals('MU')[-1]
    assert sig['status'] == 'noop' and 'corto' in sig['output']['skipped']


def test_stop_loss_is_a_signal_and_goes_through_the_service(agent, alpaca, monkeypatch):
    monkeypatch.setitem(agent, 'universe', [])
    alpaca.positions = [{'symbol': 'ETHUSD', 'asset_class': 'crypto', 'qty': '0.5', 'unrealized_plpc': '-0.10',
                         'market_value': '1500', 'current_price': '3000', 'side': 'long'}]
    server._agent_run_cycle()
    sent = alpaca.posts()[-1][3]
    assert sent['symbol'] == 'ETH/USD' and sent['side'] == 'sell' and sent['qty'] == '0.5'
    assert sent['time_in_force'] == 'gtc'
    sig = _signals('ETHUSD')[-1]
    assert sig['status'] == 'executed' and sig['output']['stop_loss_pl_pct'] == -10.0


def test_big_stop_loss_is_not_blocked_by_the_per_order_cap(agent, alpaca, monkeypatch):
    """Revisión batch E: el stop-loss de una posición de US$150.000 se envía (las salidas nunca tuvieron tope por
    orden); antes quedaba «over_cap» en cada ciclo mientras la pérdida crecía."""
    monkeypatch.setitem(agent, 'universe', [])
    alpaca.positions = [{'symbol': 'NVDA', 'asset_class': 'us_equity', 'qty': '1500', 'unrealized_plpc': '-0.10',
                         'market_value': '150000', 'current_price': '100', 'side': 'long'}]
    n = len(alpaca.posts())
    server._agent_run_cycle()
    assert len(alpaca.posts()) == n + 1
    sent = alpaca.posts()[-1][3]
    assert sent['symbol'] == 'NVDA' and sent['side'] == 'sell' and sent['qty'] == '1500'
    row = _q("SELECT meta FROM broker_orders WHERE client_order_id = :c", c=sent['client_order_id'])[0]
    assert row['meta']['checks_mode'] == 'house_reduce'


def test_agent_needs_a_human_unless_paper():
    from brokerage import service
    assert service._requires_approval('agent', 'paper') is False
    assert service._requires_approval('agent', 'live') is True
    assert service._requires_approval('ui', 'live') is False
    assert service._requires_approval('mcp', 'paper') is True        # sin BROKERAGE_AUTO_APPROVE_PAPER


def test_config_is_persisted_and_the_agent_stays_off_after_a_deploy(agent, alpaca, monkeypatch):
    """BRECHAS #14 (por defecto): encendido + configuración en el libro; un despliegue (proceso nuevo) lo deja
    APAGADO con aviso bilingüe y la MISMA configuración."""
    monkeypatch.setattr(server._trading_agent, '_agent_thread_fn', lambda: None)
    monkeypatch.setitem(agent, 'running', False)
    monkeypatch.setitem(server._AGENT_RESTORE, 'done', True)
    c = server.app.test_client()
    h = {'Content-Type': 'application/json', 'X-Trade-Pin': PIN}
    r = c.post('/api/trade/agent/start', headers=h,
               data=json.dumps({'mode': 'auto', 'max_pos_pct': 3.5, 'universe': ['NVDA', 'AMD'], 'interval_min': 30}))
    assert r.status_code == 200 and r.get_json()['status'] == 'started'
    last = _q("SELECT output, principal_id FROM decisions WHERE kind = 'policy.change' "
              "AND subject->>'policy' = 'trade.agent_config' ORDER BY seq DESC LIMIT 1")[0]
    assert last['output']['running'] is True and last['output']['config']['max_pos_pct'] == 3.5
    assert last['principal_id'] == 'op:fabrizio'
    # ── «despliegue»: proceso nuevo = memoria vacía con los valores por defecto ──
    monkeypatch.setitem(agent, 'running', False)
    monkeypatch.setitem(agent, 'mode', 'manual')
    monkeypatch.setitem(agent, 'max_pos_pct', 5.0)
    monkeypatch.setitem(agent, 'universe', ['NVDA'])
    monkeypatch.setitem(agent, 'log', [])
    agent.pop('notice', None)
    monkeypatch.setitem(server._AGENT_RESTORE, 'done', False)
    st = c.get('/api/trade/agent/status', headers=h).get_json()
    assert st['running'] is False and st['mode'] == 'auto' and st['max_pos_pct'] == 3.5
    assert st['universe'] == ['NVDA', 'AMD'] and st['interval_min'] == 30
    assert st['notice']['es'].startswith('⏸') and 'update' in st['notice']['en']
    assert any('APAGADO' in (x.get('msg') or '') for x in st['log'])
    last = _q("SELECT output, principal_id FROM decisions WHERE kind = 'policy.change' "
              "AND subject->>'policy' = 'trade.agent_config' ORDER BY seq DESC LIMIT 1")[0]
    assert last['output']['running'] is False and last['output']['reason'] == 'stopped_by_restart'
    assert last['principal_id'] == 'system:trading_agent'
    # un segundo «despliegue» ya no avisa (quedó anotado como apagado)
    agent.pop('notice', None)
    monkeypatch.setitem(server._AGENT_RESTORE, 'done', False)
    assert c.get('/api/trade/agent/status', headers=h).get_json()['notice'] is None
    # encenderlo borra el aviso
    r = c.post('/api/trade/agent/start', headers=h, data='{}')
    assert r.get_json()['status'] == 'started' and server._AGENT.get('notice') is None


def test_fills_are_append_only_and_land_as_outcomes(alpaca):
    from sqlalchemy import text
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        res = service.house_order(s, 'QCOM', 'buy', qty=4, client_order_id='kh-fill-0000001', requested_by='pytest')
    assert res['ok'] and res['status'] == 'submitted', res
    sub = res['decision_id']
    o = alpaca.orders['kh-fill-0000001']
    o.update(status='partially_filled', filled_qty='1', filled_avg_price='101.5')
    assert service.poll_fills_job()['updated'] >= 1
    o.update(status='filled', filled_qty='4', filled_avg_price='101.25')
    service.poll_fills_job()
    from brokerage.models import BrokerOrder
    with session_scope() as s:                    # lo que quedó abierto de otras pruebas (otro bróker falso)
        for r in s.query(BrokerOrder).filter(BrokerOrder.status.in_(('submitted', 'partially_filled', 'approved'))):
            r.status = 'canceled'
    assert service.poll_fills_job() == {'open': 0}                 # nada abierto: ni siquiera llama a Alpaca
    fills = _q("SELECT cum_qty, delta_qty, avg_price, status, decision_id FROM broker_fills "
               "WHERE alpaca_order_id = :a ORDER BY id", a=o['id'])
    assert [(f['cum_qty'], f['delta_qty']) for f in fills] == [(1.0, 1.0), (4.0, 3.0)]
    assert fills[-1]['status'] == 'filled' and fills[-1]['decision_id'] == sub
    outs = _q("SELECT outcome_kind, result FROM decision_outcomes WHERE decision_id = CAST(:d AS uuid) ORDER BY id",
              d=sub)
    kinds = [x['outcome_kind'] for x in outs]
    assert kinds.count('fill') == 2 and 'order_status' in kinds
    assert outs[-1]['result']['status'] == 'filled'
    with session_scope() as s:                    # sondear otra vez lo mismo no duplica
        r = s.query(service.BrokerOrder).filter(service.BrokerOrder.client_order_id == 'kh-fill-0000001').one()
        assert service._record_fill(s, r, 0.0) is False          # (orden, 4) ya existe: no inserta
    assert len(_q("SELECT 1 FROM broker_fills WHERE alpaca_order_id = :a", a=o['id'])) == 2
    with pytest.raises(Exception) as ei:
        with session_scope() as s:
            s.execute(text("UPDATE broker_fills SET cum_qty = 99 WHERE alpaca_order_id = :a"), {'a': o['id']})
    assert 'append-only' in str(ei.value)
