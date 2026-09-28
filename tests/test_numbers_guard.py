"""Guardián de cifras en TODA llamada de IA (core/ai._ai_complete)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import ai  # noqa: E402


def _fake(responses, calls):
    def f(system, prompt, max_tokens, tier='fast', model=None):
        calls.append((system, prompt))
        return responses.pop(0), 'fake'
    return f


def _patch(monkeypatch, responses, calls):
    monkeypatch.setattr(ai, 'CLAUDE', '')
    monkeypatch.setattr(ai, 'AI_ORDER', ['gemini'])
    monkeypatch.setitem(ai._AI_PROVIDERS, 'gemini', (lambda: True, _fake(responses, calls)))


def test_cifra_de_memoria_se_corrige_con_reintento(monkeypatch):
    calls = []
    _patch(monkeypatch, ['Broadcom vale ~$350B.', 'Broadcom vale ~$1.1T según el dato en vivo.'], calls)
    text, _ = ai._ai_complete('Analista', 'Datos: AVGO market_cap_usd_b=1105.2', 500)
    assert '$1.1T' in text and '⚠' not in text
    assert len(calls) == 2 and '$350B' in calls[1][1]
    assert 'REGLA DE CIFRAS' in calls[0][0]


def test_cifra_que_persiste_queda_marcada(monkeypatch):
    calls = []
    _patch(monkeypatch, ['Vale $350B.', 'Sigue valiendo $350B.'], calls)
    text, _ = ai._ai_complete('Analista', 'Datos: market_cap_usd_b=1105.2', 500)
    assert '$350B (⚠ cifra no verificada)' in text


def test_cifras_del_input_pasan_sin_reintento(monkeypatch):
    calls = []
    _patch(monkeypatch, ['{"texto": "Ingresos de $51.6B y precio $235"}'], calls)
    text, _ = ai._ai_complete('Analista', 'ingresos 2024: 51.6B, price=235.4', 500)
    assert len(calls) == 1 and '⚠' not in text
    assert ai._extract_json(text)['texto'].startswith('Ingresos')


def test_marca_en_ingles_y_json_sigue_valido(monkeypatch):
    calls = []
    _patch(monkeypatch, ['{"summary": "The company is worth $350B and growing"}'] * 2, calls)
    text, _ = ai._ai_complete('Analyst', 'market cap 1105B', 500)
    assert 'unverified figure' in ai._extract_json(text)['summary']
