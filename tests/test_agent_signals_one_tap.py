"""«1 toque» (2026-10-20): en modo MANUAL el agente PROPONE señales listas (lado, monto, precio visto, stop, motivo) y
una persona las aprueba con su PIN; salen por EL camino único (brokerage.service.house_order, source='ui'). Vencen,
no se usan dos veces y se rechazan si el precio se movió en contra. El agente ve además el técnico de cierres reales y
la convicción de los analistas, con una guarda fija (no compra en sobrecompra extrema). Sin red y sin base (papel)."""
import json
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

import server  # noqa: E402
from tests.test_order_single_path import H, _clean, alpaca, client, nodb, spies  # noqa: E402,F401

TA = server._trading_agent


@pytest.fixture
def manual(monkeypatch, alpaca, nodb):
    for k, v in (('running', True), ('mode', 'manual'), ('universe', ['AMD']), ('log', []), ('pending_close', {}),
                 ('daily_pnl_pct', 0.0), ('min_confidence', 65), ('max_orders_per_cycle', 3), ('max_pos_pct', 5.0),
                 ('stop_loss_pct', 3.0), ('signals', {})):
        monkeypatch.setitem(server._AGENT, k, v)
    monkeypatch.setattr(TA, '_agent_analyze', lambda *a, **k: {'action': 'buy', 'confidence': 90,
                                                               'reason': 'demanda de IA', 'size_pct': 2})
    monkeypatch.setattr(TA, '_agent_context', lambda t: {'tech': {'rsi14': 55.0, 'trend': 'alcista'},
                                                         'conviction': 40.0, 'lines': []})
    monkeypatch.setattr(TA, '_agent_tone', lambda t: 0.0)
    monkeypatch.setattr(server, 'FINNHUB', 'fh')
    monkeypatch.setattr(server, '_fetch_quote_raw', lambda t, timeout=8: ({'c': 100.0, 'pc': 99.0}, None))
    return server._AGENT


def _pending():
    return [s for s in server._AGENT['signals'].values() if s['status'] == 'pending']


def test_manual_cycle_proposes_a_ready_signal_and_sends_nothing(manual, alpaca, spies):
    server._agent_run_cycle()
    assert not spies['submits'] and not alpaca.posts()
    (s,) = _pending()
    assert s['ticker'] == 'AMD' and s['side'] == 'buy' and s['notional'] == 200.0      # 2 % de 10.000
    assert s['price'] == 100.0 and s['rsi14'] == 55.0 and s['conviction'] == 40.0 and s['paper'] is True
    assert s['stop_loss_pct'] == 3.0 and s['reason'] == 'demanda de IA'


def test_one_tap_takes_the_signal_through_the_single_path_once(manual, alpaca, spies, client):
    server._agent_run_cycle()
    (s,) = _pending()
    r = client.get('/api/trade/agent/signals', headers=H())
    assert r.status_code == 200 and r.get_json()['signals'][0]['id'] == s['id']
    r = client.post(f"/api/trade/agent/signals/{s['id']}/take", data='{}', headers=H())
    assert r.status_code == 200, r.get_json()
    assert spies['checks'] >= 1 and spies['submits'] == ['kh-sig-' + s['id']]
    assert float(alpaca.posts()[-1][3]['notional']) == 200.0
    r = client.post(f"/api/trade/agent/signals/{s['id']}/take", data='{}', headers=H())   # segundo toque: no
    assert r.status_code == 409 and len(spies['submits']) == 1


def test_take_needs_the_pin(manual, client):
    server._agent_run_cycle()
    (s,) = _pending()
    r = client.post(f"/api/trade/agent/signals/{s['id']}/take", data='{}', headers={'Content-Type': 'application/json'})
    assert r.status_code in (401, 403)


def test_price_moved_against_or_expired_is_refused(manual, alpaca, spies, client, monkeypatch):
    server._agent_run_cycle()
    (s,) = _pending()
    monkeypatch.setattr(server, '_fetch_quote_raw', lambda t, timeout=8: ({'c': 102.0, 'pc': 99.0}, None))
    r = client.post(f"/api/trade/agent/signals/{s['id']}/take", data='{}', headers=H())
    assert r.status_code == 409 and r.get_json()['code'] == 'price_moved' and not spies['submits']
    s['expires_ts'] = time.time() - 1
    r = client.post(f"/api/trade/agent/signals/{s['id']}/take", data='{}', headers=H())
    assert r.status_code == 409 and r.get_json()['code'] == 'signal_expired'


def test_dismiss(manual, client):
    server._agent_run_cycle()
    (s,) = _pending()
    r = client.post(f"/api/trade/agent/signals/{s['id']}/dismiss", data='{}', headers=H())
    assert r.status_code == 200 and server._AGENT['signals'][s['id']]['status'] == 'dismissed'


def test_guard_blocks_buying_overbought(manual, monkeypatch, alpaca):
    monkeypatch.setattr(TA, '_agent_context', lambda t: {'tech': {'rsi14': 81.0}, 'conviction': None, 'lines': []})
    server._agent_run_cycle()
    assert not _pending()
    assert 'RSI 81.0' in [e for e in server._AGENT['log'] if e.get('ticker') == 'AMD'][-1]['skipped']


def test_manual_stop_loss_becomes_an_exit_signal(manual, alpaca, spies, client, monkeypatch):
    alpaca.positions = [{'symbol': 'NVDA', 'qty': '3', 'side': 'long', 'market_value': '270', 'current_price': '90',
                         'unrealized_plpc': '-0.10', 'asset_class': 'us_equity'}]
    monkeypatch.setitem(manual, 'universe', ['NVDA'])
    server._agent_run_cycle()
    (s,) = [x for x in _pending() if x['kind'] == 'stop']
    assert s['side'] == 'sell' and s['qty'] == 3.0 and not spies['submits']
    monkeypatch.setattr(server, '_fetch_quote_raw', lambda t, timeout=8: ({'c': 80.0, 'pc': 99.0}, None))
    r = client.post(f"/api/trade/agent/signals/{s['id']}/take", data='{}', headers=H())   # salir nunca se frena
    assert r.status_code == 200, r.get_json()
    assert alpaca.posts()[-1][3]['side'] == 'sell' and alpaca.posts()[-1][3]['qty'] == '3'


def test_prompt_carries_khipus_context():
    seen = {}

    def fake(system, prompt, max_tokens=0, tier=None):
        seen['p'] = prompt
        return '{"action":"hold","confidence":10,"reason":"x","size_pct":0}', 'm'
    old = server._ai_complete
    server._ai_complete = fake
    try:
        TA._agent_analyze('AMD', 100.0, 99.0, 0.0, facts={'lines': ['RSI(14, Wilder): 55.0', "Khipus analysts' conviction: +40"]})
    finally:
        server._ai_complete = old
    assert 'RSI(14, Wilder): 55.0' in seen['p'] and 'conviction: +40' in seen['p']


def test_client_card_is_bilingual_and_shows_the_money_badge():
    src = open(os.path.join(ROOT, 'engine', 'signals.js'), encoding='utf-8').read()
    for es, en in (('🔴 DINERO REAL', '🔴 REAL MONEY'), ('🧪 SIMULADO', '🧪 PAPER'), ('Descartar', 'Dismiss'),
                   ('información, no consejo', 'information, not advice')):
        assert es in src and en in src
    assert '/api/trade/agent/signals/' in src and 'confirmOrder' in src and '_tradeFetch' in src
    assert 'window.confirm' not in src


def test_agent_panel_lives_in_the_os_broker_window():
    """«¿Dónde está el trading?» (2026-10-21): el agente se maneja desde Khipus OS (ventana «Mi cuenta (bróker)»), no
    solo desde la vista clásica; la búsqueda ⌘K lo encuentra por «agente»."""
    sig = open(os.path.join(ROOT, 'engine', 'signals.js'), encoding='utf-8').read()
    for es, en in (('Agente de trading', 'Trading agent'), ('Iniciar', 'Start'), ('Detener', 'Stop'),
                   ('Acciones a vigilar', 'Stocks to watch'), ('Automático (papel)', 'Automatic (paper)')):
        assert es in sig and en in sig
    assert "'/api/trade/agent/' + (start ? 'start' : 'stop')" in sig and 'd.auto_allowed' in sig
    cp = open(os.path.join(ROOT, 'engine', 'cockpit.js'), encoding='utf-8').read()
    assert 'bcp-bk-agent' in cp and 'KhipuSignals.agentBox' in cp and 'agente trading bot' in cp


def test_without_finnhub_the_agent_uses_the_app_quote_cascade_and_says_when_no_price(manual, monkeypatch):
    """«No empieza el agente» (2026-10-21): sin Finnhub (sin clave o con su límite agotado) saltaba TODAS las acciones
    en silencio. Ahora usa la cascada de precios de la app (Finnhub → Yahoo) y, si no hay precio, lo deja escrito."""
    from core import quotes
    monkeypatch.setattr(server, 'FINNHUB', '')
    monkeypatch.setattr(quotes, 'fetch_quotes_live', lambda t, **k: {'quotes': {'AMD': {'close': 100.0, 'prev': 99.0,
                                                                                    'live': 100.0, 'src': 'yahoo'}}})
    server._agent_run_cycle()
    (s,) = _pending()
    assert s['ticker'] == 'AMD' and s['price'] == 100.0
    msgs = [e.get('msg') or '' for e in server._AGENT['log']]
    assert any('Revisando 1 acciones' in m for m in msgs) and any('Revisión terminada: 1 con precio' in m for m in msgs)
    monkeypatch.setitem(server._AGENT, 'signals', {})
    monkeypatch.setattr(quotes, 'fetch_quotes_live', lambda t, **k: {'quotes': {}})
    server._agent_run_cycle()
    assert not _pending() and any('Sin precio ahora' in (e.get('msg') or '') and 'AMD' in e['msg'] for e in server._AGENT['log'])
