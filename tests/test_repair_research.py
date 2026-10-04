"""tests/test_repair_research.py — Misión de reparación (2026-10-04), P0 · Investigación.

Cada test fija un arreglo de REPAIR_LOG.md: fallaba antes del commit y pasa
después. Sin red; los tests con base se saltan sin DATABASE_URL.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_infra import _Resp, _fake_anthropic, _httpx  # noqa: E402

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


@pytest.fixture(autouse=True)
def _circuitos_limpios(monkeypatch):
    """Cada test arranca con todos los corta-circuitos cerrados."""
    from core import ai
    monkeypatch.setattr(ai, '_CIRCUIT', {})
    yield


def _api_error(code, message):
    import anthropic
    httpx = _httpx()
    req = httpx.Request('POST', 'https://api.anthropic.test/v1/messages')
    resp = httpx.Response(code, request=req, json={'type': 'error', 'error': {'type': 'invalid_request_error',
                                                                               'message': message}})
    return anthropic.APIStatusError(message, response=resp, body={'error': {'message': message}})


# ════════════════════════════════════════════════════════════════════════════
# R1 · Corta-circuito por proveedor (sin saldo / clave inválida / modelo retirado)
# ════════════════════════════════════════════════════════════════════════════

def test_r1_claude_sin_saldo_abre_el_circuito_y_no_se_vuelve_a_llamar(monkeypatch):
    from core import ai
    err = _api_error(400, 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing.')
    calls = _fake_anthropic(monkeypatch, [err])
    monkeypatch.setattr(ai, 'AI_MODEL_FAST', 'claude-a')
    monkeypatch.setattr(ai, 'AI_MODEL_DEEP', 'claude-a')
    with pytest.raises(RuntimeError):
        ai._complete_claude('s', 'p', 10, model='claude-a')
    n = len(calls)
    assert n >= 1
    st = ai.ai_circuit_state()['claude']
    assert st['open'] is True and st['kind'] == 'credit' and st['seconds_left'] > 0
    assert 'saldo' in st['reason_es'].lower() and st['reason_en']
    # segunda llamada: NO toca la red, falla al instante con un mensaje bilingüe
    with pytest.raises(RuntimeError) as ei:
        ai._complete_claude('s', 'p', 10, model='claude-a')
    assert len(calls) == n
    assert 'en pausa' in str(ei.value) and 'paused' in str(ei.value)
    assert ai.provider_available('claude') is False
    assert ai._ai_configured() is True            # "configurado" sigue significando "hay clave"
    # pasado el tiempo de pausa vuelve a intentar
    monkeypatch.setattr(ai, '_mono', lambda: ai.time.monotonic() + 3601)
    with pytest.raises(RuntimeError):
        ai._complete_claude('s', 'p', 10, model='claude-a')
    assert len(calls) > n


def test_r1_la_cascada_salta_el_proveedor_en_pausa_sin_tocar_la_red(monkeypatch):
    import anthropic

    from core import ai

    class Boom:
        def __init__(self, **kw):
            raise AssertionError('no debe construirse el cliente de Anthropic con el circuito abierto')

    monkeypatch.setattr(anthropic, 'Anthropic', Boom)
    monkeypatch.setattr(ai, 'CLAUDE', 'sk-test-123456')
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    monkeypatch.setattr(ai, 'AI_ORDER', ['claude', 'gemini'])
    monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: _Resp(
        200, {'candidates': [{'content': {'parts': [{'text': 'desde gemini'}]}}]}))
    ai._open_circuit('claude', 'credit', 'sin saldo', 600)
    text, used = ai._ai_complete_raw('s', 'p', 10)
    assert text == 'desde gemini' and used.startswith('gemini:')


def test_r1_errores_pasajeros_no_abren_el_circuito(monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    monkeypatch.setattr(ai, 'AI_TRANSIENT_RETRIES', 1)
    monkeypatch.setattr(ai, '_sleep', lambda s: None)
    for code, st in ((503, 'UNAVAILABLE'), (429, 'RESOURCE_EXHAUSTED'), (500, 'INTERNAL')):
        monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: _Resp(code, {'error': {'status': st}}))
        with pytest.raises(RuntimeError):
            ai._complete_gemini('', 'p', 10)
        assert ai.ai_circuit_state()['gemini']['open'] is False, code


def test_r1_clave_invalida_y_modelo_retirado_abren_el_circuito(monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    monkeypatch.setattr(ai, 'NVIDIA_KEY', 'nv-123456789')
    monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: _Resp(403, {'error': {'status': 'PERMISSION_DENIED'}}))
    with pytest.raises(RuntimeError):
        ai._complete_gemini('', 'p', 10)
    assert ai.ai_circuit_state()['gemini'] == pytest.approx(ai.ai_circuit_state()['gemini'])
    assert ai.ai_circuit_state()['gemini']['open'] and ai.ai_circuit_state()['gemini']['kind'] == 'auth'
    monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: _Resp(410, {}))
    with pytest.raises(RuntimeError):
        ai._complete_nvidia('', 'p', 10)
    assert ai.ai_circuit_state()['nvidia']['open'] and ai.ai_circuit_state()['nvidia']['kind'] == 'model'


def test_r1_el_ping_del_diagnostico_cierra_el_circuito_si_el_proveedor_responde(monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    ai._open_circuit('gemini', 'auth', 'clave inválida', 600)
    monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: _Resp(
        200, {'candidates': [{'content': {'parts': [{'text': 'pong'}]}}]}))
    assert ai._complete_gemini('', 'ping', 1)[0] == 'pong'      # ≤ 4 tokens = ping: salta la pausa
    assert ai.ai_circuit_state()['gemini']['open'] is False


def test_r1_research_no_usa_un_proveedor_en_pausa(monkeypatch):
    from core import ai
    from research.llm import CoreProvider
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    p = CoreProvider('gemini')
    assert p.available() is True
    ai._open_circuit('gemini', 'credit', 'sin saldo', 600)
    assert p.available() is False
