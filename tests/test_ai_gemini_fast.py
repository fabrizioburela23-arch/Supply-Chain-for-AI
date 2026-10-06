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
    monkeypatch.setattr(ai, '_GEMINI_HOT', {})
    monkeypatch.setattr(ai, 'NVIDIA_KEY', '')
    seen = {}

    def gem(system, prompt, max_tokens, tier='fast', json_mode=False, **kw):
        seen['json_mode'] = json_mode; seen['timeout_s'] = kw.get('timeout_s')
        return '{"ok": 1}', 'gemini:x'
    monkeypatch.setitem(ai._AI_PROVIDERS, 'gemini', (lambda: True, gem))
    text, used = ai._ai_complete('s', 'p', 100, 'fast', verify_numbers=False, want_json=True)
    assert seen['json_mode'] is True and json.loads(text) == {'ok': 1}


def test_flash_nivel_rapido_sin_pensamiento(monkeypatch):
    monkeypatch.setattr(ai, 'GEMINI_MODEL', 'gemini-2.5-flash')
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'g')
    monkeypatch.setattr(ai, '_GEMINI_HOT', {})
    monkeypatch.delenv('GEMINI_THINKING', raising=False)
    bodies = []

    def post(url, body, timeout, retry=True):
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


def test_gemini_3_usa_niveles_de_pensamiento(monkeypatch):
    """Gemini 3.8 Flash rechaza thinkingBudget (y 'minimal'): rápido = low, profundo = medium, con margen."""
    monkeypatch.setattr(ai, 'GEMINI_MODEL', 'gemini-3.8-flash')
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'g')
    monkeypatch.setattr(ai, '_GEMINI_HOT', {})
    monkeypatch.delenv('GEMINI_THINKING', raising=False)
    bodies = []

    def post(url, body, timeout, retry=True):
        bodies.append((url, json.loads(json.dumps(body))))
        return _gem_ok('hola')
    monkeypatch.setattr(ai, '_gemini_post', post)
    text, used = ai._complete_gemini_inner('s', 'p', 200, 'fast')
    url, b = bodies[-1]
    assert 'models/gemini-3.8-flash:generateContent' in url and used == 'gemini:gemini-3.8-flash'
    assert b['generationConfig']['thinkingConfig'] == {'thinkingLevel': 'low'}
    assert b['generationConfig']['maxOutputTokens'] == 200 + 1024 and len(bodies) == 1   # sin el 400 de antes
    ai._complete_gemini_inner('s', 'p', 200, 'deep')
    assert bodies[-1][1]['generationConfig']['thinkingConfig'] == {'thinkingLevel': 'medium'}
    ai._complete_gemini_inner('s', 'p', 3000, 'deep', json_mode=True)
    g = bodies[-1][1]['generationConfig']
    # investigación (JSON + profundo): calidad primero → medium
    assert g['thinkingConfig'] == {'thinkingLevel': 'medium'} and g['maxOutputTokens'] == 8192 + 2048
    ai._complete_gemini_inner('s', 'p', 1600, 'fast', json_mode=True)                  # paso del chat → low
    assert bodies[-1][1]['generationConfig']['thinkingConfig'] == {'thinkingLevel': 'low'}
    assert ai._gemini_major('models/gemini-3.8-flash') == 3 and ai._gemini_major('gemini-2.5-flash') == 2
    assert ai._gemini_major('otro') == 0


def test_precio_gemini_38():
    from core import ai_usage
    assert ai_usage.price_for('gemini', 'gemini-3.8-flash') == (0.75, 3.75)


class _Err:
    def __init__(self, code, status):
        self.status_code, self.ok, self._s = code, False, status

    def json(self):
        return {'error': {'status': self._s}}


def test_gemini_saturado_usa_el_modelo_de_respaldo(monkeypatch):
    """Producción 2026-10-06: gemini-3.8-flash → 503 UNAVAILABLE. El mismo pedido va a gemini-3.5-flash."""
    monkeypatch.setattr(ai, 'GEMINI_MODEL', 'gemini-3.8-flash')
    monkeypatch.setattr(ai, 'GEMINI_FALLBACK_MODEL', 'gemini-3.5-flash')
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'g')
    monkeypatch.setattr(ai, '_GEMINI_HOT', {})
    urls = []

    def post(url, body, timeout, retry=True):
        urls.append(url)
        return _Err(503, 'UNAVAILABLE') if 'gemini-3.8-flash' in url else _gem_ok('hola')
    monkeypatch.setattr(ai, '_gemini_post', post)
    text, used = ai._complete_gemini_inner('s', 'p', 200, 'fast')
    assert text == 'hola' and used == 'gemini:gemini-3.5-flash' and len(urls) == 2
    # un error de clave NO salta al respaldo (no lo arreglaría)
    monkeypatch.setattr(ai, '_gemini_post', lambda u, b, t, **k: _Err(403, 'PERMISSION_DENIED'))
    import pytest
    with pytest.raises(RuntimeError, match='Gemini HTTP 403 PERMISSION_DENIED'):
        ai._complete_gemini_inner('s', 'p', 200, 'fast')
    # los dos saturados → el error del último, como antes (y entonces la cascada pasa a NVIDIA)
    monkeypatch.setattr(ai, '_gemini_post', lambda u, b, t, **k: _Err(503, 'UNAVAILABLE'))
    with pytest.raises(RuntimeError, match='Gemini HTTP 503 UNAVAILABLE'):
        ai._complete_gemini_inner('s', 'p', 200, 'fast')
    # sin respaldo
    monkeypatch.setattr(ai, 'GEMINI_FALLBACK_MODEL', 'off')
    assert ai._gemini_models() == ['gemini-3.8-flash']


def test_respaldos_en_cadena_y_saturados_al_final(monkeypatch):
    """Saturación general de Google (5-6 oct-2026): 3.8 y 3.5 Flash con 503 a la vez → prueba 3.1 Pro,
    sin esperar reintentos entre modelos; los saturados quedan al final unos minutos."""
    monkeypatch.setattr(ai, 'GEMINI_MODEL', 'gemini-3.8-flash')
    monkeypatch.setattr(ai, 'GEMINI_FALLBACK_MODEL', 'gemini-3.5-flash, gemini-3.1-pro,gemini-2.5-flash')
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'g')
    monkeypatch.setattr(ai, '_GEMINI_HOT', {})
    monkeypatch.setattr(ai, '_sleep', lambda s: (_ for _ in ()).throw(AssertionError('no debe esperar entre modelos')))
    urls = []

    def post(url, body, timeout, retry=True):
        urls.append(url.split('/models/')[1].split(':')[0])
        return _gem_ok('ok') if 'gemini-3.1-pro' in url else _Err(503, 'UNAVAILABLE')
    monkeypatch.setattr(ai, '_gemini_post', post)
    text, used = ai._complete_gemini_inner('s', 'p', 200, 'fast')
    assert used == 'gemini:gemini-3.1-pro' and urls == ['gemini-3.8-flash', 'gemini-3.5-flash', 'gemini-3.1-pro']
    st = ai.gemini_state()
    assert st['models'] == ['gemini-3.1-pro', 'gemini-2.5-flash', 'gemini-3.8-flash', 'gemini-3.5-flash']
    assert set(st['saturated']) == {'gemini-3.8-flash', 'gemini-3.5-flash'}
    urls.clear()
    ai._complete_gemini_inner('s', 'p', 200, 'fast')               # la siguiente va directo al que funciona
    assert urls == ['gemini-3.1-pro']
