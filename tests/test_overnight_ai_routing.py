"""Overnight 2026-10-10 (Fabrizio pagó Claude, Gemini y TypeSafe): la IA da BUENAS respuestas y gasta bien.

1. Orden de proveedores POR NIVEL (core/ai.provider_order): profundo = AI_ORDER_DEEP > claude,gemini,nvidia (la
   AI_ORDER vieja se ignora); rápido = AI_ORDER_FAST > AI_ORDER > gemini,claude,nvidia.
2. Parámetros de Claude por modelo (core/ai.claude_attempts): Sonnet 5.5 nunca recibe thinking 'disabled' (400) ni
   temperature; Opus 5.5 / Fable nunca 'disabled'; Haiku 4.5 igual que siempre. Un 400 por thinking reintenta el
   MISMO modelo con parámetros más seguros (antes degradaba a Haiku en silencio).
3. Chat: con Jev en 'needs_deep_reasoning' la respuesta FINAL usa el nivel profundo; elegir herramientas, el rápido.
4. Jev manda en el chat por defecto si hay clave (DECIDE_CONTROL sin poner); 'off' lo apaga.
"""
import json
import os
import sys
from concurrent.futures import Future

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import ai  # noqa: E402
from core import ai_usage  # noqa: E402
from core import decide  # noqa: E402
from core import khipu_chat as kc  # noqa: E402


def _httpx():
    try:
        import httpx2 as hx
    except ImportError:  # pragma: no cover
        import httpx as hx
    return hx


@pytest.fixture(autouse=True)
def _limpio(monkeypatch):
    """Sin variables de orden del entorno, AI_ORDER "de fábrica" (no puesta), circuitos cerrados."""
    for k in ('AI_ORDER_FAST', 'AI_ORDER_DEEP'):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(ai, 'AI_ORDER_EXPLICIT', False)
    monkeypatch.setattr(ai, 'AI_ORDER', ai._AI_ORDER_FROM_CONFIG)
    monkeypatch.setattr(ai, '_CIRCUIT', {})
    monkeypatch.setattr(ai, '_sleep', lambda s: None)
    yield


# ════════════════════════════════════════════════════════════════════════════
# 1 · orden por nivel
# ════════════════════════════════════════════════════════════════════════════

def test_orden_por_defecto_sin_ninguna_variable():
    assert ai.provider_order('fast') == ['gemini', 'claude', 'nvidia']
    assert ai.provider_order('deep') == ['claude', 'gemini', 'nvidia']


def test_ai_order_vieja_solo_manda_en_el_nivel_rapido(monkeypatch):
    # lo que hay hoy en Railway: el parche de emergencia de cuando Claude no tenía saldo
    monkeypatch.setattr(ai, 'AI_ORDER_EXPLICIT', True)
    monkeypatch.setattr(ai, 'AI_ORDER', ['gemini', 'nvidia', 'claude'])
    assert ai.provider_order('fast') == ['gemini', 'nvidia', 'claude']
    assert ai.provider_order('deep') == ['claude', 'gemini', 'nvidia']      # IGNORADA a propósito en profundo
    st = ai.ai_route_state()
    assert st['fast_source'] == 'AI_ORDER' and st['deep_source'] == 'default'
    assert st['legacy_ignored_for_deep'] is True and 'AI_ORDER_FAST' in st['hint_es'] and st['hint_en']


def test_variables_por_nivel_ganan(monkeypatch):
    monkeypatch.setattr(ai, 'AI_ORDER_EXPLICIT', True)
    monkeypatch.setattr(ai, 'AI_ORDER', ['nvidia', 'gemini', 'claude'])
    monkeypatch.setenv('AI_ORDER_FAST', 'claude, Gemini')
    monkeypatch.setenv('AI_ORDER_DEEP', 'gemini')
    assert ai.provider_order('fast') == ['claude', 'gemini', 'nvidia']      # los que faltan van al final
    assert ai.provider_order('deep') == ['gemini', 'claude', 'nvidia']
    st = ai.ai_route_state()
    assert st['fast_source'] == 'AI_ORDER_FAST' and st['deep_source'] == 'AI_ORDER_DEEP'
    # basura en la variable → se ignora y manda el siguiente en la precedencia
    monkeypatch.setenv('AI_ORDER_FAST', 'openai,,')
    monkeypatch.setenv('AI_ORDER_DEEP', 'xx')
    assert ai.provider_order('fast') == ['nvidia', 'gemini', 'claude']
    assert ai.provider_order('deep') == ['claude', 'gemini', 'nvidia']


def test_ai_order_reemplazada_por_codigo_cuenta_como_puesta(monkeypatch):
    monkeypatch.setattr(ai, 'AI_ORDER', ['claude', 'gemini'])
    assert ai.provider_order('fast') == ['claude', 'gemini', 'nvidia']
    assert ai.provider_order('deep') == ['claude', 'gemini', 'nvidia']


def _fake_providers(monkeypatch, calls):
    def mk(name):
        def f(system, prompt, max_tokens, tier='fast', **kw):
            calls.append((name, tier, kw.get('model')))
            return f'desde {name}', f'{name}:x'
        return f
    monkeypatch.setattr(ai, '_AI_PROVIDERS', {n: (lambda: True, mk(n)) for n in ('claude', 'gemini', 'nvidia')})


def test_la_cascada_usa_el_orden_del_nivel(monkeypatch):
    calls = []
    _fake_providers(monkeypatch, calls)
    assert ai._ai_complete_raw('s', 'p', 100, tier='deep')[0] == 'desde claude'
    assert ai._ai_complete_raw('s', 'p', 100, tier='fast')[0] == 'desde gemini'
    # quien pide un modelo Claude concreto quiere Claude, aunque el nivel rápido empiece por Gemini
    assert ai._ai_complete_raw('s', 'p', 100, tier='fast', model='claude-sonnet-5')[0] == 'desde claude'
    assert calls == [('claude', 'deep', None), ('gemini', 'fast', None), ('claude', 'fast', 'claude-sonnet-5')]


def test_claude_sin_saldo_se_salta_en_profundo(monkeypatch):
    calls = []
    _fake_providers(monkeypatch, calls)
    ai._open_circuit('claude', 'credit', 'credit balance too low', 600)
    text, used = ai._ai_complete_raw('s', 'p', 100, tier='deep')
    assert text == 'desde gemini' and calls == [('gemini', 'deep', None)]


def test_estado_de_ruta_para_el_diagnostico(monkeypatch):
    monkeypatch.setattr(ai, 'AI_MODEL_FAST', 'claude-haiku-4-5')
    monkeypatch.setattr(ai, 'AI_MODEL_DEEP', 'claude-sonnet-5-5')
    st = ai.ai_route_state()
    assert st['fast'] == ['gemini', 'claude', 'nvidia'] and st['deep'] == ['claude', 'gemini', 'nvidia']
    assert st['models']['deep'] == 'claude-sonnet-5-5' and st['models']['fast'] == 'claude-haiku-4-5'
    assert st['deep_claude']['thinking_mode'] == 'between_tools'
    assert st['deep_claude']['params'] == {'output_config': {'effort': 'medium'}}
    assert st['fast_claude']['params'] == {'thinking': {'type': 'disabled'}}
    assert isinstance(st['fast_available'], list) and st['legacy_ai_order'] is None
    json.dumps(st)                                   # serializable (🩺 / MCP / /api/health)
    from research import health
    r = health._routing()
    assert r['deep'][0] == 'claude' and r['fast_source'] == 'default'


def test_modelo_profundo_por_defecto_es_sonnet_55():
    import importlib

    from core import config
    if os.getenv('AI_MODEL_DEEP'):
        pytest.skip('AI_MODEL_DEEP puesto en el entorno')
    assert importlib.reload(config).AI_MODEL_DEEP == 'claude-sonnet-5-5'
    assert config.AI_MODEL_FAST == (os.getenv('AI_MODEL_FAST') or 'claude-haiku-4-5')


# ════════════════════════════════════════════════════════════════════════════
# 2 · parámetros de Claude por modelo
# ════════════════════════════════════════════════════════════════════════════
_SAMPLING = ('temperature', 'top_p', 'top_k')


def _flat(attempts):
    return [kw for kw, _mt in attempts]


def test_version_de_modelos():
    assert ai._claude_version('claude-sonnet-5-5') == ('sonnet', (5, 5))
    assert ai._claude_version('claude-haiku-4-5-20251001') == ('haiku', (4, 5))
    assert ai._claude_version('claude-sonnet-5') == ('sonnet', (5, 0))
    assert ai._claude_version('anthropic.claude-opus-5-5') == ('opus', (5, 5))
    assert ai._claude_version('claude-fable-5-1') == ('fable', (5, 1))
    assert ai._claude_version('claude-a') == (None, None)
    assert ai.claude_thinking_mode('claude-sonnet-5-5') == 'between_tools'
    for m in ('claude-opus-5-5', 'claude-fable-5-1', 'claude-fable-5', 'claude-mythos-5-1'):
        assert ai.claude_thinking_mode(m) == 'always', m
    for m in ('claude-haiku-4-5', 'claude-sonnet-5', 'claude-opus-5', 'claude-opus-4-8', 'claude-a'):
        assert ai.claude_thinking_mode(m) == 'legacy', m
    assert ai.claude_thinking_mode('claude-haiku-5-5') == 'haiku55'


def test_sonnet_55_nunca_recibe_disabled_ni_temperature():
    for tier in ('fast', 'deep'):
        for mt in (4, 900, 1600, 3000, 8000):
            att = ai.claude_attempts('claude-sonnet-5-5', tier, mt)
            for kw in _flat(att):
                assert (kw.get('thinking') or {}).get('type') != 'disabled', (tier, mt)
                assert not any(k in kw for k in _SAMPLING)
                th = kw.get('thinking')
                if th is not None:                 # between_tools: sin ningún otro campo dentro
                    assert th == {'type': 'between_tools'}
                    assert (kw.get('output_config') or {}).get('effort') in (None, 'low', 'medium', 'high')
            assert att[-1][0] == {}                # el último intento es siempre "sin nada" (válido en todo modelo)
    fast = ai.claude_attempts('claude-sonnet-5-5', 'fast', 1600)
    assert fast[0] == ({'thinking': {'type': 'between_tools'}}, 1600)
    deep = ai.claude_attempts('claude-sonnet-5-5', 'deep', 1600)
    assert deep[0] == ({'output_config': {'effort': 'medium'}}, 4800)      # adaptativo + esfuerzo medio + margen
    assert ai.claude_attempts('claude-sonnet-5-5', 'deep', 900)[0][1] == 4000
    assert ai.claude_attempts('claude-sonnet-5-5', 'deep', 8000)[0][1] == 16000   # tope sin streaming
    assert ai.claude_attempts('claude-sonnet-5-5', 'deep', 20000)[0][1] == 20000  # nunca MENOS de lo pedido


def test_opus_55_y_fable_nunca_apagan_el_pensamiento():
    for m in ('claude-opus-5-5', 'claude-fable-5-1', 'claude-mythos-5-1'):
        for tier, effort in (('fast', 'low'), ('deep', 'medium')):
            att = ai.claude_attempts(m, tier, 1000)
            assert all('thinking' not in kw for kw in _flat(att)), m
            assert all(not any(k in kw for k in _SAMPLING) for kw in _flat(att))
            assert att[0][0] == {'output_config': {'effort': effort}} and att[0][1] >= 3000


def test_haiku_45_y_modelos_viejos_sin_cambios():
    for m in ('claude-haiku-4-5', 'claude-sonnet-5', 'claude-opus-4-8', 'claude-a'):
        for tier in ('fast', 'deep'):
            assert ai.claude_attempts(m, tier, 500) == [({'thinking': {'type': 'disabled'}}, 500), ({}, 6000)]
    assert ai.claude_attempts('claude-haiku-4-5', 'fast', 2000) == [({'thinking': {'type': 'disabled'}}, 2000),
                                                                     ({}, 8000)]
    assert ai.claude_attempts('claude-haiku-5-5', 'fast', 500)[0] == ({'thinking': {'type': 'disabled'}}, 500)
    assert ai.claude_attempts('claude-haiku-5-5', 'deep', 500)[0] == ({'output_config': {'effort': 'medium'}}, 4000)


def test_ping_del_diagnostico_por_modelo():
    assert ai.claude_ping_kwargs('claude-haiku-4-5') == {'thinking': {'type': 'disabled'}}
    assert ai.claude_ping_kwargs('claude-sonnet-5-5') == {'thinking': {'type': 'between_tools'}}
    assert ai.claude_ping_kwargs('claude-opus-5-5') == {}
    assert ai.claude_attempts('claude-opus-5-5', 'fast', 1)[0][1] == 1        # un ping no pide margen


# ── cliente de Anthropic falso que se comporta como la API real ──────────────

def _api_400(message):
    import anthropic
    hx = _httpx()
    req = hx.Request('POST', 'https://api.anthropic.test/v1/messages')
    resp = hx.Response(400, request=req, json={'type': 'error', 'error': {'type': 'invalid_request_error',
                                                                          'message': message}})
    return anthropic.BadRequestError(message, response=resp, body={'error': {'message': message}})


class _Block:
    def __init__(self, type_, text=''):
        self.type, self.text = type_, text
        if type_ == 'thinking':
            self.thinking = ''


class _Msg:
    def __init__(self, model, text, stop='end_turn'):
        self.model, self.stop_reason = model, stop
        self.content = [_Block('thinking'), _Block('text', text)]       # el pensamiento viene VACÍO
        self.usage = None


def _fake_anthropic(monkeypatch, reject):
    """reject(kw) → mensaje de error 400 o None. Registra cada llamada (modelo, kwargs)."""
    import anthropic
    calls = []

    class FakeClient:
        def __init__(self, **kw):
            self.messages = self

        def create(self, **kw):
            calls.append(kw)
            msg = reject(kw)
            if msg:
                raise _api_400(msg)
            return _Msg(kw['model'], f"respuesta de {kw['model']}")

    monkeypatch.setattr(ai, 'CLAUDE', 'sk-test-123456')
    monkeypatch.setattr(anthropic, 'Anthropic', FakeClient)
    return calls


def _api_rules(kw):
    """Las reglas de la API real (oct-2026) que importan aquí."""
    m, th = kw['model'], (kw.get('thinking') or {}).get('type')
    if any(k in kw for k in _SAMPLING) and ('5-5' in m or 'fable' in m):
        return 'temperature: non-default sampling parameters are not supported for this model'
    if m == 'claude-sonnet-5-5' and th == 'disabled':
        return ('"thinking.type.disabled" is not supported for this model. Use "thinking.type.between_tools" '
                'for the lowest thinking setting, or "thinking.type.adaptive" and "output_config.effort" to '
                'control thinking behavior.')
    if m in ('claude-opus-5-5', 'claude-fable-5-1') and th == 'disabled':
        return '"thinking.type.disabled" is not supported for this model.'
    if th == 'between_tools' and m != 'claude-sonnet-5-5':
        return '"thinking.type.between_tools" is not supported for this model.'
    return None


def test_sonnet_55_profundo_no_degrada_a_haiku(monkeypatch):
    calls = _fake_anthropic(monkeypatch, _api_rules)
    monkeypatch.setattr(ai, 'AI_MODEL_DEEP', 'claude-sonnet-5-5')
    monkeypatch.setattr(ai, 'AI_MODEL_FAST', 'claude-haiku-4-5')
    text, used = ai._complete_claude('s', 'p', 1000, tier='deep')
    assert used == 'claude-sonnet-5-5' and text == 'respuesta de claude-sonnet-5-5'
    assert [c['model'] for c in calls] == ['claude-sonnet-5-5']           # una sola llamada, sin Haiku
    assert calls[0]['output_config'] == {'effort': 'medium'} and 'thinking' not in calls[0]
    assert calls[0]['max_tokens'] == 4000
    # nivel rápido con Sonnet 5.5 como modelo rápido: between_tools, sin margen extra
    calls.clear()
    monkeypatch.setattr(ai, 'AI_MODEL_FAST', 'claude-sonnet-5-5')
    text, used = ai._complete_claude('s', 'p', 800, tier='fast')
    assert used == 'claude-sonnet-5-5' and calls[0]['thinking'] == {'type': 'between_tools'}
    assert calls[0]['max_tokens'] == 800 and not any(k in calls[0] for k in _SAMPLING)


def test_un_400_por_thinking_reintenta_el_mismo_modelo(monkeypatch):
    """Si la API rechaza un parámetro de pensamiento (p. ej. cambia la regla), se prueba el MISMO modelo con
    parámetros más seguros; nunca se salta a Haiku en silencio."""
    def strict(kw):
        if kw['model'] == 'claude-sonnet-5-5' and 'thinking' in kw:
            return '"thinking.type.between_tools" is not supported for this model.'
        return None
    calls = _fake_anthropic(monkeypatch, strict)
    monkeypatch.setattr(ai, 'AI_MODEL_FAST', 'claude-sonnet-5-5')
    text, used = ai._complete_claude('s', 'p', 800, tier='fast')
    assert used == 'claude-sonnet-5-5'
    assert [c['model'] for c in calls] == ['claude-sonnet-5-5', 'claude-sonnet-5-5']
    assert calls[1]['output_config'] == {'effort': 'low'} and 'thinking' not in calls[1]
    assert calls[1]['max_tokens'] == 4000


def test_regla_vieja_disabled_en_sonnet_55_tampoco_degrada(monkeypatch):
    """El bug que se arregla: si algo manda 'disabled' a Sonnet 5.5 (modelo forzado por tarea), el 400 de la API
    no lleva a Haiku: el mismo modelo responde con el intento siguiente."""
    calls = _fake_anthropic(monkeypatch, _api_rules)
    monkeypatch.setattr(ai, 'claude_attempts', lambda m, tier, mt: [({'thinking': {'type': 'disabled'}}, mt), ({}, 6000)])
    text, used = ai._complete_claude('s', 'p', 500, tier='deep', model='claude-sonnet-5-5')
    assert used == 'claude-sonnet-5-5'
    assert [c['model'] for c in calls] == ['claude-sonnet-5-5', 'claude-sonnet-5-5']
    assert all(c['model'] != 'claude-haiku-4-5' for c in calls)


def test_400_que_no_es_de_parametros_sigue_al_siguiente_modelo(monkeypatch):
    def no_access(kw):
        return 'model: claude-sonnet-5-5 is not available for this key' if kw['model'] == 'claude-sonnet-5-5' else None
    calls = _fake_anthropic(monkeypatch, no_access)
    monkeypatch.setattr(ai, 'AI_MODEL_DEEP', 'claude-sonnet-5-5')
    monkeypatch.setattr(ai, 'AI_MODEL_FAST', 'claude-haiku-4-5')
    text, used = ai._complete_claude('s', 'p', 500, tier='deep')
    assert used == 'claude-haiku-4-5' and [c['model'] for c in calls] == ['claude-sonnet-5-5', 'claude-haiku-4-5']


def test_rechazo_de_seguridad_pasa_a_otro_modelo(monkeypatch):
    import anthropic
    calls = []

    class FakeClient:
        def __init__(self, **kw):
            self.messages = self

        def create(self, **kw):
            calls.append(kw['model'])
            if kw['model'] == 'claude-opus-5-5':
                return _Msg('claude-opus-5-5', '', stop='refusal')
            return _Msg(kw['model'], 'ok')
    monkeypatch.setattr(ai, 'CLAUDE', 'sk-test-123456')
    monkeypatch.setattr(anthropic, 'Anthropic', FakeClient)
    monkeypatch.setattr(ai, 'AI_MODEL_FAST', 'claude-haiku-4-5')
    monkeypatch.setattr(ai, 'AI_MODEL_DEEP', 'claude-sonnet-5-5')
    text, used = ai._complete_claude('s', 'p', 500, tier='deep', model='claude-opus-5-5')
    assert used == 'claude-sonnet-5-5' and calls == ['claude-opus-5-5', 'claude-sonnet-5-5']   # 1 sola vez a Opus


def test_cuerpo_real_del_sdk(monkeypatch):
    """Con el SDK de verdad (transporte simulado): el JSON que sale hacia la API."""
    import anthropic
    hx = _httpx()
    bodies = []

    def handler(req):
        body = json.loads(req.content)
        bodies.append(body)
        th = (body.get('thinking') or {}).get('type')
        if body['model'] == 'claude-sonnet-5-5' and th == 'disabled':
            return hx.Response(400, json={'type': 'error', 'error': {
                'type': 'invalid_request_error', 'message': '"thinking.type.disabled" is not supported for this model.'}})
        return hx.Response(200, json={
            'id': 'msg_1', 'type': 'message', 'role': 'assistant', 'model': body['model'],
            'content': [{'type': 'thinking', 'thinking': '', 'signature': 'x'}, {'type': 'text', 'text': 'hola'}],
            'stop_reason': 'end_turn', 'stop_sequence': None, 'usage': {'input_tokens': 5, 'output_tokens': 3}})

    real = anthropic.Anthropic

    def factory(**kw):
        return real(http_client=anthropic.DefaultHttpxClient(transport=hx.MockTransport(handler)), **kw)
    monkeypatch.setattr(anthropic, 'Anthropic', factory)
    monkeypatch.setattr(ai, 'CLAUDE', 'sk-test-123456')
    monkeypatch.setattr(ai, 'AI_MODEL_DEEP', 'claude-sonnet-5-5')
    ai_usage._reset_for_tests()
    text, used = ai._complete_claude('s', 'p', 1200, tier='deep')
    assert (text, used) == ('hola', 'claude-sonnet-5-5') and len(bodies) == 1
    assert bodies[0]['output_config'] == {'effort': 'medium'} and 'thinking' not in bodies[0]
    assert not any(k in bodies[0] for k in _SAMPLING)
    rows = [r for r in ai_usage.report(days=1)['recent'] if r['provider'] == 'claude']
    assert rows and rows[0]['model'] == 'claude-sonnet-5-5'


def test_timeout_del_chat_llega_a_claude(monkeypatch):
    import anthropic
    made = []

    class FakeClient:
        def __init__(self, **kw):
            made.append(kw)
            self.messages = self

        def create(self, **kw):
            return _Msg(kw['model'], 'ok')
    monkeypatch.setattr(ai, 'CLAUDE', 'sk-test-123456')
    monkeypatch.setattr(anthropic, 'Anthropic', FakeClient)
    ai._complete_claude('s', 'p', 100, tier='deep', timeout_s=12)
    ai._complete_claude('s', 'p', 100, tier='deep')
    assert made[0]['timeout'] == 12 and made[1]['timeout'] == ai.CLAUDE_TIMEOUT_DEEP_S


def test_precios_actuales():
    p = ai_usage.price_for
    assert p('claude', 'claude-sonnet-5-5') == (2.0, 10.0) and p('claude', 'claude-opus-5-5') == (4.0, 20.0)
    assert p('claude', 'claude-haiku-4-5') == (1.0, 5.0) and p('claude', 'claude-sonnet-5') == (2.0, 10.0)
    assert p('claude', 'claude-fable-5-1') == (10.0, 50.0) and p('claude', 'claude-haiku-5-5') == (0.1, 0.5)
    assert p('claude', 'claude-mythos-5-1') == (10.0, 50.0)
    assert p('typesafe', 'jev-1.13.0') == (0.04, 0.0)


# ════════════════════════════════════════════════════════════════════════════
# 3 · chat: respuesta final en el nivel profundo cuando Jev dice "análisis"
# ════════════════════════════════════════════════════════════════════════════

def _jev(route, conf=0.9):
    return {'route': {'choice': route, 'confidence': conf}, 'mentions_company': {'noul': 0.9},
            'asks_trade': {'noul': 0.0}, 'about_portfolio': {'noul': 0.0}, 'urgency': {'score': 1}}


@pytest.fixture
def offline(monkeypatch):
    from mcp_server import tools as mt
    monkeypatch.setattr(mt, '_live_profile', lambda sym: {'available': False, 'reason': 'test (offline)'})
    monkeypatch.setattr(mt._auth, 'db_available', lambda: False)
    monkeypatch.setattr(decide, '_persist', lambda row: None)
    monkeypatch.setattr('core.live_facts.live_facts_block', lambda m: '')
    monkeypatch.setattr(ai, '_ai_configured', lambda: True)


@pytest.fixture
def jev(monkeypatch, offline):
    monkeypatch.setenv('TYPESAFE_API_KEY', 'ts-test')
    monkeypatch.delenv('DECIDE_CONTROL', raising=False)          # por defecto: Jev manda en el chat
    box = {'ans': _jev('needs_deep_reasoning')}
    monkeypatch.setattr(decide, 'ask', lambda state, q, feature=None, timeout=None: box['ans'])
    return box


class ScriptAI:
    """Falso _ai_complete: anota el nivel de cada llamada; respuestas por nivel."""

    def __init__(self, fast, deep):
        self.fast, self.deep, self.calls = list(fast), list(deep), []

    def __call__(self, system, prompt, max_tokens=1000, tier='fast', **kw):
        self.calls.append(tier)
        q = self.deep if tier == 'deep' else self.fast
        item = q.pop(0) if q else {'final': {'answer': 'Listo.', 'actions': []}}
        return (item if isinstance(item, str) else json.dumps(item)), f'fake:{tier}'


def test_analisis_la_respuesta_final_la_escribe_el_profundo(monkeypatch, jev):
    ai_ = ScriptAI(fast=[{'tool': 'search_companies', 'args': {'query': 'TSMC'}},
                         {'final': {'answer': 'Respuesta rápida.', 'actions': []}}],
                   deep=[{'final': {'answer': 'Análisis profundo de la dependencia de Nvidia en TSMC.', 'actions': []}}])
    monkeypatch.setattr(ai, '_ai_complete', ai_)
    out = kc.run_chat('compara el riesgo de Nvidia y AMD por su dependencia de TSMC', [], 'es', {})
    assert ai_.calls == ['fast', 'fast', 'deep']                 # herramientas en rápido, final en profundo
    assert out['answer'].startswith('Análisis profundo') and out['model'] == 'fake:deep'
    assert out['router']['route'] == 'needs_deep_reasoning' and out['router']['final_tier'] == 'deep'
    assert out['router']['by'] == 'jev' and out['steps'] == 3


def test_analisis_si_el_profundo_falla_queda_la_respuesta_rapida(monkeypatch, jev):
    ai_ = ScriptAI(fast=[{'final': {'answer': 'Respuesta rápida.', 'actions': []}}], deep=['no es json {'])
    monkeypatch.setattr(ai, '_ai_complete', ai_)
    out = kc.run_chat('¿cuál es la tesis de Nvidia a 3 años?', [], 'es', {})
    assert ai_.calls == ['fast', 'deep'] and out['answer'] == 'Respuesta rápida.' and out['model'] == 'fake:fast'


def test_analisis_la_redaccion_en_prosa_tambien_es_profunda(monkeypatch, jev):
    seen = []

    def fake_synth(message, history, lang, context, scratch, timeout, tier='fast'):
        seen.append(tier)
        return 'Redacción profunda con los datos consultados, completa.', f'fake:{tier}'
    monkeypatch.setattr(kc, 'synthesize', fake_synth)
    ai_ = ScriptAI(fast=['{"esto no": "es el protocolo"}', '{"tampoco": 1}'], deep=[])
    monkeypatch.setattr(ai, '_ai_complete', ai_)
    out = kc.run_chat('¿cuál es la tesis de Nvidia a 3 años?', [], 'es', {})
    assert seen == ['deep'] and out['answer'].startswith('Redacción profunda') and out['model'] == 'fake:deep'


def test_otras_rutas_no_cambian(monkeypatch, jev):
    jev['ans'] = _jev('needs_tools')
    ai_ = ScriptAI(fast=[{'tool': 'search_companies', 'args': {'query': 'TSMC'}},
                         {'final': {'answer': 'Corta.', 'actions': []}}], deep=[])
    monkeypatch.setattr(ai, '_ai_complete', ai_)
    out = kc.run_chat('¿quién le vende a nvidia?', [], 'es', {})
    assert ai_.calls == ['fast', 'fast'] and out['answer'] == 'Corta.' and 'final_tier' not in out['router']


def test_sin_jev_todo_en_rapido(monkeypatch, offline):
    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    monkeypatch.delenv('TYPESAFE_KEY', raising=False)
    ai_ = ScriptAI(fast=[{'final': {'answer': 'Hola.', 'actions': []}}], deep=[])
    monkeypatch.setattr(ai, '_ai_complete', ai_)
    out = kc.run_chat('¿cuál es la tesis de Nvidia?', [], 'es', {})
    assert ai_.calls == ['fast'] and out['router'] == {'by': 'default'}


def test_synthesize_pasa_el_nivel(monkeypatch):
    tiers = []

    def fake(system, prompt, max_tokens, tier='fast', **kw):
        tiers.append(tier)
        return 'Una respuesta en prosa limpia y completa para el usuario.', 'fake'
    monkeypatch.setattr(ai, '_ai_complete', fake)
    kc.synthesize('q', [], 'es', {}, [], 10)
    kc.synthesize('q', [], 'es', {}, [], 10, tier='deep')
    kc._call_ai('s', 'p', 5)
    kc._call_ai('s', 'p', 5, tier='deep')
    assert tiers == ['fast', 'deep', 'fast', 'deep']


# ════════════════════════════════════════════════════════════════════════════
# 4 · Jev manda en el chat por defecto si hay clave
# ════════════════════════════════════════════════════════════════════════════

def _done(v):
    f = Future()
    f.set_result(v)
    return f


def test_jev_control_por_defecto(monkeypatch):
    monkeypatch.setenv('TYPESAFE_API_KEY', 'ts-test')
    monkeypatch.delenv('DECIDE_ENABLED', raising=False)
    monkeypatch.delenv('DECIDE_CONTROL', raising=False)
    assert decide.control_features() == ['chat_gate']
    assert decide.control('chat_gate') and not decide.control('news')
    assert decide.chat_plan(_done(_jev('needs_tools')))['route'] == 'needs_tools'
    monkeypatch.setenv('DECIDE_CONTROL', '')                       # vacía = sin poner
    assert decide.control('chat_gate')
    for off in ('off', 'OFF', 'none', '0', 'false'):
        monkeypatch.setenv('DECIDE_CONTROL', off)
        assert not decide.control('chat_gate'), off
        assert decide.chat_plan(_done(_jev('needs_tools'))) is None
    monkeypatch.setenv('DECIDE_CONTROL', 'news')                    # lista explícita: solo esa
    assert not decide.control('chat_gate') and decide.control('news')
    monkeypatch.setenv('DECIDE_CONTROL', 'all')
    assert decide.control('chat_gate') and decide.control('cualquiera')


def test_jev_sin_clave_nunca_manda(monkeypatch):
    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    monkeypatch.delenv('TYPESAFE_KEY', raising=False)
    monkeypatch.delenv('DECIDE_CONTROL', raising=False)
    assert not decide.control('chat_gate') and decide.chat_plan(_done(_jev('local_fact'))) is None
    monkeypatch.setenv('TYPESAFE_API_KEY', 'ts-test')
    monkeypatch.setenv('DECIDE_ENABLED', 'off')                      # interruptor general
    assert not decide.control('chat_gate')


def test_jev_reglas_de_seguridad_intactas(monkeypatch):
    monkeypatch.setenv('TYPESAFE_API_KEY', 'ts-test')
    monkeypatch.delenv('DECIDE_CONTROL', raising=False)
    monkeypatch.delenv('DECIDE_ENABLED', raising=False)
    assert decide.chat_plan(_done(_jev('local_fact', conf=0.3))) is None                  # poca confianza
    order = _jev('local_fact')
    order['asks_trade'] = {'noul': 0.9}
    assert decide.chat_plan(_done(order)) is None                                          # parece una orden
    assert decide.chat_plan(Future(), wait_s=0.01) is None                                 # no llegó a tiempo


def test_reporte_de_sombra_dice_quien_manda(monkeypatch):
    monkeypatch.setenv('TYPESAFE_API_KEY', 'ts-test')
    monkeypatch.delenv('DECIDE_CONTROL', raising=False)
    monkeypatch.delenv('DECIDE_ENABLED', raising=False)
    monkeypatch.setattr('ontology.db.ontology_available', lambda: False)
    rep = decide.shadow_report(days=1)
    assert rep['control_features'] == ['chat_gate'] and 'MANDA' in rep['note_es'] and 'CONTROL' in rep['note_en']
    monkeypatch.setenv('DECIDE_CONTROL', 'off')
    rep = decide.shadow_report(days=1)
    assert rep['control_features'] == [] and 'sombra' in rep['note_es']
