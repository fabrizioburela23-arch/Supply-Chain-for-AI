"""_ai_json: si la respuesta no es JSON, reintenta en Gemini json_mode (2026-10-04)."""
from core import ai


def test_ai_json_reintenta_en_gemini_json_mode(monkeypatch):
    calls = []
    monkeypatch.setattr(ai, '_ai_complete', lambda *a, **k: ('Claro, aquí va mi análisis en prosa…', 'nvidia:x'))
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'g')

    def gem(system, prompt, max_tokens, tier='fast', json_mode=False):
        calls.append(json_mode)
        return ('{"tesis": "ok"}', 'gemini:flash')
    monkeypatch.setattr(ai, '_complete_gemini', gem)
    parsed, used = ai._ai_json('s', 'p', 100)
    assert parsed == {'tesis': 'ok'} and used == 'gemini:flash' and calls == [True]


def test_ai_json_sin_gemini_lanza_mensaje_claro(monkeypatch):
    monkeypatch.setattr(ai, '_ai_complete', lambda *a, **k: ('prosa sin json', 'claude'))
    monkeypatch.setattr(ai, 'GEMINI_KEY', '')
    try:
        ai._ai_json('s', 'p', 100)
        assert False
    except ValueError as e:
        assert 'formato esperado' in str(e)


def test_ai_json_devuelve_directo_si_ya_es_json(monkeypatch):
    monkeypatch.setattr(ai, '_ai_complete', lambda *a, **k: ('```json\n{"a": 1}\n```', 'claude'))
    assert ai._ai_json('s', 'p', 100)[0] == {'a': 1}


def test_mensaje_amable_del_servidor():
    import server
    msg, _ = server._ai_friendly_error(ValueError('Expecting value: line 1 column 1 (char 0)'))
    assert 'no respondió' in msg and 'did not answer' in msg
    msg2, _ = server._ai_friendly_error(ValueError('la IA respondió pero no en el formato esperado (JSON)'))
    assert 'formato esperado' in msg2
