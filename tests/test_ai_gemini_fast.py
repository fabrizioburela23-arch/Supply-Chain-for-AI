"""Gemini como único proveedor (2026-10-04): JSON estricto en los pasos del chat y sin pensamiento en el nivel rápido."""
import json

from core import ai


class _R:
    def __init__(self, body):
        self.status_code, self.ok, self._b = 200, True, body

    def json(self):
        return self._b


def _gem_ok(text):
    return _R({'candidates': [{'content': {'parts': [{'text': text}]}, 'finishReason': 'STOP'}],
               'usageMetadata': {'promptTokenCount': 10, 'candidatesTokenCount': 5}})


def test_want_json_llega_a_gemini_como_json_mode(monkeypatch):
    monkeypatch.setattr(ai, 'CLAUDE', '')
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'g')
    monkeypatch.setattr(ai, 'NVIDIA_KEY', '')
    seen = {}

    def gem(system, prompt, max_tokens, tier='fast', json_mode=False, **kw):
        seen['json_mode'] = json_mode; seen['timeout_s'] = kw.get('timeout_s')
        return '{"ok": 1}', 'gemini:x'
    monkeypatch.setitem(ai._AI_PROVIDERS, 'gemini', (lambda: True, gem))
    text, used = ai._ai_complete('s', 'p', 100, 'fast', verify_numbers=False, want_json=True)
    assert seen['json_mode'] is True and json.loads(text) == {'ok': 1}


def test_flash_nivel_rapido_sin_pensamiento(monkeypatch):
    monkeypatch.setattr(ai, 'GEMINI_MODEL', 'gemini-3.5-flash')
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'g')
    monkeypatch.delenv('GEMINI_THINKING', raising=False)
    bodies = []

    def post(url, body, timeout):
        bodies.append(body)
        return _gem_ok('hola')
    monkeypatch.setattr(ai, '_gemini_post', post)
    ai._complete_gemini_inner('s', 'p', 200, 'fast')
    assert bodies[-1]['generationConfig'].get('thinkingConfig') == {'thinkingBudget': 0}
    ai._complete_gemini_inner('s', 'p', 200, 'deep')
    g = bodies[-1]['generationConfig']                                   # el nivel profundo sí piensa, acotado
    assert g.get('thinkingConfig') == {'thinkingBudget': 1024} and g['maxOutputTokens'] == 200 + 1024
    ai._complete_gemini_inner('s', 'p', 200, 'deep', json_mode=True)
    assert bodies[-1]['generationConfig']['responseMimeType'] == 'application/json'
    assert bodies[-1]['generationConfig'].get('thinkingConfig') == {'thinkingBudget': 0}


def test_chat_pide_json_estricto(monkeypatch):
    from core import khipu_chat as kc
    seen = {}

    def fake(system, prompt, max_tokens, tier, **kw):
        seen.update(kw); seen['tier'] = tier
        return '{"final": {"answer": "ok", "actions": []}}', 'gemini:x'
    monkeypatch.setattr(kc._ai, '_ai_complete', fake)
    kc._call_ai('s', 'p', 5)
    assert seen.get('want_json') is True and seen['tier'] == 'fast'
