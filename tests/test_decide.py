"""Jev (TypeSafe) — core/decide.py: adaptador, sombra y portero del chat."""
import json

import pytest

from core import ai_usage, decide


class _Resp:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = body or {}

    def json(self):
        return self._body


JEV = {
    'model': 'jev-1.13.0',
    'answers': {
        'route': {'type': 'choice', 'choice': 'needs_tools', 'confidence': 0.8,
                  'probabilities': {'needs_tools': 0.86, 'local_fact': 0.1, 'needs_deep_reasoning': 0.04, 'offtopic': 0.0}},
        'mentions_company': {'type': 'noul', 'noul': 0.97},
        'asks_trade': {'type': 'noul', 'noul': 0.02},
        'about_portfolio': {'type': 'noul', 'noul': 0.05},
        'urgency': {'type': 'score', 'score': 1.0, 'confidence': 0.9, 'probabilities': {'0': 0.05, '1': 0.9, '2': 0.05}},
    },
    'usage': {'input_tokens': 120, 'output_tokens': 20},
}


@pytest.fixture
def jev(monkeypatch):
    monkeypatch.setenv('TYPESAFE_API_KEY', 'ts-test')
    monkeypatch.delenv('DECIDE_ENABLED', raising=False)
    monkeypatch.delenv('DECIDE_CONTROL', raising=False)
    ai_usage._reset_for_tests()
    calls = []

    def fake_post(url, json=None, timeout=None, headers=None):
        calls.append({'url': url, 'body': json, 'headers': headers, 'timeout': timeout})
        return _Resp(200, JEV)
    monkeypatch.setattr(decide.requests, 'post', fake_post)
    return calls


def test_sin_clave_no_hace_nada(monkeypatch):
    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    monkeypatch.delenv('TYPESAFE_KEY', raising=False)
    assert not decide.available()
    assert decide.ask('hola', {'q': {'type': 'noul', 'instructions': 'x'}}) is None
    assert decide.chat_gate_start('hola') is None
    assert decide.chat_gate_finish(None, {}) is None


def test_ask_formato_y_registro(jev):
    ans = decide.ask({'message': '¿quién fabrica para Nvidia?'}, decide.CHAT_QUESTIONS, feature='khipu_chat')
    assert ans['route']['choice'] == 'needs_tools'
    body = jev[0]['body']
    assert body['model'] == 'jev-latest' and set(body['questions']) == set(decide.CHAT_QUESTIONS)
    assert body['questions']['route']['type'] == 'choice' and 'criteria' in body['questions']['route']
    assert jev[0]['headers']['Authorization'] == 'Bearer ts-test'
    # quedó en 💰 Gasto IA con tokens reales del proveedor
    rep = ai_usage.report(days=1)
    rows = [r for r in rep['recent'] if r['provider'] == 'typesafe']
    assert rows and rows[0]['tokens_in'] == 120 and rows[0]['tokens_out'] == 20 and rows[0]['feature'] == 'khipu_chat'


def test_error_http_devuelve_none(jev, monkeypatch):
    monkeypatch.setattr(decide.requests, 'post', lambda *a, **k: _Resp(500, {}))
    assert decide.ask('x', decide.CHAT_QUESTIONS) is None


def test_presupuesto_bloquea(jev, monkeypatch):
    def boom(provider, max_tokens=None):
        raise ai_usage.AIBudgetError('tope', 'cap', 'daily')
    monkeypatch.setattr(ai_usage, 'check', boom)
    assert decide.ask('x', decide.CHAT_QUESTIONS) is None
    assert not jev   # no se llamó al proveedor


def test_control_por_funcion(monkeypatch, jev):
    # 2026-10-10: con clave y DECIDE_CONTROL sin poner, Jev manda en el chat (y en nada más)
    assert decide.control('chat_gate') and not decide.control('news')
    monkeypatch.setenv('DECIDE_CONTROL', 'off')
    assert not decide.control('chat_gate')
    monkeypatch.setenv('DECIDE_CONTROL', 'chat_gate')
    assert decide.control('chat_gate') and not decide.control('news')


def test_portero_en_sombra_compara(jev):
    fut = decide.chat_gate_start('¿qué noticias hay de TSMC?', 'es')
    assert fut is not None
    fut.result(timeout=5)
    out = {'steps': 1, 'tools_used': [{'name': 'get_news', 'ok': True}], 'answer_source': 'ai', 'elapsed_ms': 900}
    dec = decide.chat_gate_finish(fut, out, '¿qué noticias hay de TSMC?')
    assert dec['route'] == 'needs_tools' and dec['mentions_company'] == 0.97
    rep = decide.shadow_report(days=1)
    f = [x for x in rep['features'] if x['feature'] == 'chat_gate'][0]
    assert f['n'] >= 1 and f['agree'] >= 1 and f['control'] is True      # 2026-10-10: manda por defecto con clave
    assert rep['recent'][0]['actual']['route'] == 'needs_tools' and rep['recent'][0]['agree'] is True


def test_ruta_real_desacuerdo(jev):
    fut = decide.chat_gate_start('explica la tesis de Nvidia vs AMD a 3 años')
    fut.result(timeout=5)
    out = {'steps': 4, 'tools_used': [{'name': 'a'}, {'name': 'b'}, {'name': 'c'}], 'answer_source': 'ai'}
    decide.chat_gate_finish(fut, out, 'tesis')
    assert decide.shadow_report()['recent'][0]['agree'] is False


def test_run_chat_sigue_igual_sin_jev(monkeypatch):
    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    from core import khipu_chat as kc
    out = kc.run_chat('hola', [], 'es', {})
    assert 'answer' in out
