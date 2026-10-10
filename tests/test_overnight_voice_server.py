"""tests/test_overnight_voice_server.py — Khipu (voz) ↔ ElevenLabs Agents, contrato oct-2026.

Sin red: un ElevenLabs FALSO (FakeEL) responde a las rutas REST que usa
core/voice_agent.py / server.py. Cubre:
  · URL firmada: ruta nueva get-signed-url (+ respaldo get_signed_url SOLO si la
    ruta no existe), agent_id del server (no el del navegador), errores en ES/EN
    con arreglo y código HTTP útil, pistas de overrides para el navegador, la
    clave nunca sale en la respuesta;
  · clasificación de errores (clave inválida, permisos de clave restringida,
    cuota en 401, 404, 429, 422, red);
  · diagnóstico 🩺 accionable (plan gratis, cuota, agente, LLM retirado, TTS
    deprecado/solo-inglés, herramientas faltantes, eventos, overrides) y la
    tarjeta /api/diagnostics;
  · sync: herramientas como RECURSOS (/v1/convai/tools + tool_ids, nunca
    `tools` en línea si hay ids), reuso por nombre e idempotencia, TTS
    (turbo_v2 → flash_v2_5 conservando la voz; eleven_v4 NO se toca), LLM
    retirado, client_events, overrides solo con ELEVENLABS_ALLOW_OVERRIDE,
    respaldo legacy/prompt cuando el PATCH se rechaza;
  · agent-tune valida el modelo; bixby-prompt acepta ELEVENLABS_ALLOW_OVERRIDE=1;
  · los topes de las herramientas del server son los mismos que usa voice.js.
"""
import copy
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

import requests  # noqa: E402

import server  # noqa: E402
from core import voice_agent as va  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = 'sk_el_TEST_KEY_DO_NOT_LEAK_999'
AGENT = 'agent_01testkhipu'
PIN = '4321-strong-pin'


class R:
    def __init__(self, status, payload=None, text=None):
        self.status_code = status
        self.ok = 200 <= status < 300
        self._payload = payload
        self.text = text if text is not None else (json.dumps(payload) if payload is not None else '')

    def json(self):
        if self._payload is None:
            raise ValueError('no json')
        return self._payload


def _merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _merge(dst[k], v)
        else:
            dst[k] = copy.deepcopy(v)


def agent_cfg(**kw):
    cfg = {
        'agent_id': AGENT, 'name': 'Khipu',
        'conversation_config': {
            'agent': {'language': 'es', 'first_message': 'Hola, soy Khipu.',
                      'prompt': {'prompt': 'viejo', 'llm': 'gemini-3.5-flash', 'tool_ids': []}},
            'tts': {'model_id': 'eleven_flash_v2_5', 'voice_id': 'voz_es_1',
                    'agent_output_audio_format': 'pcm_24000'},
            'asr': {'user_input_audio_format': 'pcm_16000'},
            'conversation': {'client_events': ['audio', 'interruption', 'user_transcript', 'agent_response']},
        },
        'platform_settings': {'overrides': {'conversation_config_override': {
            'agent': {'language': False, 'first_message': False, 'prompt': {'prompt': False}}}}},
    }
    for path, val in kw.items():
        node = cfg
        parts = path.split('__')
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = val
    return cfg


class FakeEL:
    """ElevenLabs falso: estado de agente/herramientas/suscripción + fallos inyectables."""

    def __init__(self, agent=None, tools=None, sub=None, fail=None):
        self.agent = agent if agent is not None else agent_cfg()
        self.tools = dict(tools or {})
        self.sub = sub if sub is not None else {'tier': 'creator', 'status': 'active', 'character_count': 1000,
                                                'character_limit': 100000, 'next_character_count_reset_unix': 1790000000,
                                                'can_extend_character_limit': False}
        self.fail = dict(fail or {})        # (METHOD, path) -> R | [R, R…] (uno por llamada)
        self.calls = []
        self._n = 0

    def _path(self, url):
        assert url.startswith('https://api.elevenlabs.io/'), url
        return url[len('https://api.elevenlabs.io'):]

    def _fail(self, method, path):
        f = self.fail.get((method, path))
        if isinstance(f, list):
            return f.pop(0) if f else None
        return f

    def _rec(self, method, url, headers, params=None, body=None):
        assert (headers or {}).get('xi-api-key') == KEY
        path = self._path(url)
        self.calls.append({'method': method, 'path': path, 'params': params, 'json': copy.deepcopy(body)})
        return path

    def get(self, url, params=None, headers=None, timeout=None, **_):
        path = self._rec('GET', url, headers, params=params)
        f = self._fail('GET', path)
        if f:
            return f
        if path == '/v1/user/subscription':
            return R(200, self.sub)
        if path in ('/v1/convai/conversation/get-signed-url', '/v1/convai/conversation/get_signed_url'):
            return R(200, {'signed_url': f'wss://api.elevenlabs.io/v1/convai/conversation?agent_id={params["agent_id"]}'
                                         '&conversation_signature=sig123'})
        if path == f'/v1/convai/agents/{AGENT}':
            return R(200, copy.deepcopy(self.agent)) if self.agent else R(404, {'detail': {'status': 'agent_not_found',
                                                                                         'message': 'Agent not found'}})
        if path == '/v1/convai/tools':
            return R(200, {'tools': [{'id': i, 'tool_config': c} for i, c in self.tools.items()], 'has_more': False})
        if path.startswith('/v1/convai/tools/'):
            tid = path.rsplit('/', 1)[1]
            return R(200, {'id': tid, 'tool_config': self.tools[tid]}) if tid in self.tools else R(404, {'detail': 'x'})
        if path.startswith('/v1/voices/'):
            return R(200, {'voice_id': path.rsplit('/', 1)[1], 'name': 'Valentina'})
        return R(404, {'detail': 'Not Found'})

    def post(self, url, json=None, headers=None, timeout=None, **_):
        path = self._rec('POST', url, headers, body=json)
        f = self._fail('POST', path)
        if f:
            return f
        if path == '/v1/convai/tools':
            self._n += 1
            tid = f'tool_{self._n}'
            self.tools[tid] = copy.deepcopy(json['tool_config'])
            return R(200, {'id': tid, 'tool_config': json['tool_config']})
        return R(404, {'detail': 'Not Found'})

    def patch(self, url, json=None, headers=None, timeout=None, **_):
        path = self._rec('PATCH', url, headers, body=json)
        f = self._fail('PATCH', path)
        if f:
            return f
        if path == f'/v1/convai/agents/{AGENT}':
            _merge(self.agent, json)
            return R(200, self.agent)
        if path.startswith('/v1/convai/tools/'):
            tid = path.rsplit('/', 1)[1]
            self.tools[tid] = copy.deepcopy(json['tool_config'])
            return R(200, {'id': tid, 'tool_config': json['tool_config']})
        return R(404, {'detail': 'Not Found'})

    def by(self, method, path):
        return [c for c in self.calls if c['method'] == method and c['path'] == path]


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    va.forget_agent()
    monkeypatch.delenv('ELEVENLABS_ALLOW_OVERRIDE', raising=False)
    monkeypatch.delenv('ELEVENLABS_LLM', raising=False)
    from core import http as core_http
    monkeypatch.setattr(core_http, '_rate_limit', lambda *a, **k: True)
    yield
    va.forget_agent()


@pytest.fixture
def client():
    server.app.config['TESTING'] = True
    return server.app.test_client()


@pytest.fixture
def el(monkeypatch):
    fake = FakeEL()
    monkeypatch.setattr(requests, 'get', fake.get)
    monkeypatch.setattr(requests, 'post', fake.post)
    monkeypatch.setattr(requests, 'patch', fake.patch)
    monkeypatch.setattr(server, 'ELEVENLABS_KEY', KEY)
    monkeypatch.setattr(server, 'ELEVENLABS_AGENT_ID', AGENT)
    return fake


SPECS = lambda: server._bixby_client_tools()  # noqa: E731


# ════════════════════════════════════════════════════════════════════════════
# URL firmada / sesión
# ════════════════════════════════════════════════════════════════════════════
def test_signed_url_uses_current_path_and_agent_param():
    fake = FakeEL()
    res = va.get_signed_url(KEY, AGENT, fake)
    assert res['ok'] and res['signed_url'].startswith('wss://')
    c = fake.calls[0]
    assert c['path'] == '/v1/convai/conversation/get-signed-url' and c['params'] == {'agent_id': AGENT}
    assert len(fake.calls) == 1


def test_signed_url_falls_back_only_when_route_missing():
    fake = FakeEL(fail={('GET', '/v1/convai/conversation/get-signed-url'): R(404, {'detail': 'Not Found'})})
    res = va.get_signed_url(KEY, AGENT, fake)
    assert res['ok'] and fake.calls[-1]['path'] == '/v1/convai/conversation/get_signed_url'
    # 404 de AGENTE inexistente: no se reintenta en la ruta vieja, se explica
    fake2 = FakeEL(fail={('GET', '/v1/convai/conversation/get-signed-url'):
                         R(404, {'detail': {'status': 'agent_not_found', 'message': 'Agent not found'}})})
    res2 = va.get_signed_url(KEY, AGENT, fake2)
    assert not res2['ok'] and len(fake2.calls) == 1
    assert res2['error']['code'] == 'not_found' and 'ELEVENLABS_AGENT_ID' in res2['error']['fix_es']


def test_session_route_returns_url_and_override_hints(client, el):
    el.agent = agent_cfg(platform_settings={'overrides': {'conversation_config_override': {
        'agent': {'language': True, 'first_message': True, 'prompt': {'prompt': False}}}}})
    r = client.post('/api/voice/session', data=json.dumps({'agent_id': 'agent_ATTACKER'}),
                    headers={'Content-Type': 'application/json'})
    d = r.get_json()
    assert r.status_code == 200 and d['signed_url'].startswith('wss://')
    assert d['agent_id'] == AGENT and 'agent_ATTACKER' not in json.dumps(d)       # el agente lo decide el server
    assert el.calls[0]['params'] == {'agent_id': AGENT}
    assert d['overrides'] == {'prompt': False, 'language': True, 'first_message': True, 'voice_id': False}
    assert d['language'] == 'es' and d['output_format'] == 'pcm_24000' and d['input_format'] == 'pcm_16000'
    assert d['has_first_message'] is True
    assert KEY not in r.get_data(as_text=True)


@pytest.mark.parametrize('status,body,code,http', [
    (401, {'detail': {'status': 'quota_exceeded', 'message': 'This request exceeds your quota of 10000.'}},
     'quota_exceeded', 402),
    (401, {'detail': {'status': 'invalid_api_key', 'message': 'Invalid API key'}}, 'invalid_api_key', 502),
    (429, {'detail': {'status': 'too_many_concurrent_requests', 'message': 'busy'}}, 'rate_limited', 429),
])
def test_session_route_maps_errors_bilingual(client, el, status, body, code, http):
    el.fail[('GET', '/v1/convai/conversation/get-signed-url')] = R(status, body)
    r = client.post('/api/voice/session', data='{}', headers={'Content-Type': 'application/json'})
    d = r.get_json()
    assert r.status_code == http and d['code'] == code
    assert d['error'] and d['error_en'] and d['error'] != d['error_en']
    assert d.get('fix_es') and d.get('fix_en')
    assert KEY not in r.get_data(as_text=True)


def test_session_route_without_key_is_clear(client, monkeypatch):
    monkeypatch.setattr(server, 'ELEVENLABS_KEY', '')
    r = client.post('/api/voice/session', data='{}', headers={'Content-Type': 'application/json'})
    assert r.status_code == 400 and r.get_json()['code'] == 'not_configured' and r.get_json()['error_en']


def test_session_route_survives_agent_read_failure(client, el):
    el.fail[('GET', f'/v1/convai/agents/{AGENT}')] = R(500, {'detail': 'boom'})
    r = client.post('/api/voice/session', data='{}', headers={'Content-Type': 'application/json'})
    d = r.get_json()
    assert r.status_code == 200 and d['signed_url'] and 'overrides' not in d   # el navegador cae a override_env


# ════════════════════════════════════════════════════════════════════════════
# Clasificación de errores
# ════════════════════════════════════════════════════════════════════════════
def test_classify_error_codes():
    c = va.classify_error
    assert c(401, json.dumps({'detail': {'status': 'invalid_api_key', 'message': 'Invalid API key'}}))['code'] == 'invalid_api_key'
    e = c(401, {'detail': {'status': 'missing_permissions',
                           'message': 'The API key you used is missing the permission user_read to execute this operation.'}})
    assert e['code'] == 'missing_permissions' and e['permission'] == 'user_read'
    assert c(401, {'detail': {'status': 'quota_exceeded', 'message': 'exceeds your quota'}})['code'] == 'quota_exceeded'
    assert c(401, {'detail': {'status': 'detected_unusual_activity', 'message': 'Unusual activity detected. Free Tier usage disabled.'}})['code'] == 'unusual_activity'
    assert c(404, {'detail': 'Not Found'})['code'] == 'not_found'
    assert c(429, {'detail': {'status': 'system_busy'}})['code'] == 'rate_limited'
    assert c(422, {'detail': [{'loc': ['body', 'x'], 'msg': 'field required'}]})['code'] == 'validation'
    assert c(503, 'upstream')['code'] == 'server_error'
    assert c(None, exc=TimeoutError('timed out'))['code'] == 'network'
    for code in ('invalid_api_key', 'missing_permissions', 'quota_exceeded', 'unusual_activity', 'payment_required',
                 'not_found', 'rate_limited', 'validation', 'network', 'server_error'):
        d = va.describe({'code': code, 'http': 400, 'message': 'x'}, 'agent')
        assert d['es'] and d['en'] and d['es'] != d['en'], code


# ════════════════════════════════════════════════════════════════════════════
# Diagnóstico accionable
# ════════════════════════════════════════════════════════════════════════════
def _diag(fake, **kw):
    return va.diagnose(KEY, AGENT, http=fake, expected_tools=[t['name'] for t in SPECS()],
                       prompt=server.BIXBY_SYSTEM_PROMPT, full=kw.pop('full', False), **kw)


def _lvl(d, cid):
    return {c['id']: c['level'] for c in d['checks']}.get(cid)


def test_diag_no_key_and_no_agent():
    d = va.diagnose('', AGENT, http=FakeEL())
    assert not d['ok'] and not d['configured'] and 'Railway' in d['detail'] and 'QUÉ HACER' in d['detail']
    d2 = va.diagnose(KEY, '', http=FakeEL())
    assert not d2['ok'] and _lvl(d2, 'agent') == 'error' and 'ELEVENLABS_AGENT_ID' in d2['detail']


def test_diag_invalid_key_stops_early_with_fix():
    fake = FakeEL(fail={('GET', '/v1/user/subscription'): R(401, {'detail': {'status': 'invalid_api_key',
                                                                          'message': 'Invalid API key'}})})
    d = _diag(fake)
    assert not d['ok'] and d['key_error'] == 'invalid_api_key'
    assert 'API Keys' in d['detail'] and 'API Keys' in d['detail_en']
    assert not fake.by('GET', f'/v1/convai/agents/{AGENT}')


def test_diag_restricted_key_is_warning_not_failure():
    fake = FakeEL(fail={('GET', '/v1/user/subscription'): R(401, {'detail': {
        'status': 'missing_permissions', 'message': 'missing the permission user_read'}})})
    d = _diag(fake)
    assert _lvl(d, 'key') == 'warn' and d['agent_ok'] is True


def test_diag_free_plan_and_quota():
    fake = FakeEL(sub={'tier': 'free', 'status': 'free', 'character_count': 10000, 'character_limit': 10000,
                       'can_extend_character_limit': False})
    d = _diag(fake)
    assert _lvl(d, 'plan') == 'warn' and 'GRATIS' in d['detail']
    assert _lvl(d, 'quota') == 'error' and not d['ok'] and d['subscription']['pct'] == 100.0


def test_diag_agent_not_found():
    fake = FakeEL(agent={})
    fake.agent = None
    d = _diag(fake)
    assert not d['ok'] and d['agent_ok'] is False and _lvl(d, 'agent') == 'error'
    assert 'agent_' in d['detail']


def test_diag_flags_outdated_agent_with_fixes():
    fake = FakeEL(agent=agent_cfg(conversation_config__agent__prompt={'prompt': 'viejo', 'llm': 'gemini-1.5-flash',
                                                                       'tool_ids': []},
                                  conversation_config__tts={'model_id': 'eleven_turbo_v2', 'voice_id': 'v1'}))
    d = _diag(fake, full=True)
    lv = {c['id']: c['level'] for c in d['checks']}
    assert lv['llm'] == 'error' and lv['tts'] == 'error' and lv['tools'] == 'error'
    assert lv['events'] == 'error'          # sin client_tool_call
    assert lv['prompt'] == 'warn' and lv['overrides'] == 'info'
    assert not d['ok'] and d['fixes'] and 'Redeploy' in d['detail']
    assert d['agent']['llm_legacy'] is True and d['agent']['tts_fix'] == 'eleven_flash_v2_5'
    assert d['voice_name'] == 'Valentina'


def test_diag_all_good_after_sync():
    fake = FakeEL()
    res = va.sync_agent(KEY, AGENT, server.BIXBY_SYSTEM_PROMPT, SPECS(), http=fake)
    assert res['ok'], res
    d = _diag(fake)
    lv = {c['id']: c['level'] for c in d['checks']}
    assert lv['tools'] == 'ok' and lv['events'] == 'ok' and lv['prompt'] == 'ok' and lv['tts'] == 'ok'
    assert d['ok'] and d['tools']['missing'] == []


def test_diagnostics_card_uses_actionable_detail(client, el, monkeypatch):
    el.agent = agent_cfg(conversation_config__tts={'model_id': 'eleven_flash_v2', 'voice_id': 'v1'})
    card = server._diag_elevenlabs()
    assert card['configured'] and not card['ok']
    assert 'QUÉ HACER' in card['detail'] and card['detail_en'] and card['fixes']
    assert KEY not in json.dumps(card)
    r = client.get('/api/voice/agent-diag')
    d = r.get_json()
    assert r.status_code == 200 and d['tts_model'] == 'eleven_flash_v2' and d['voice_name'] == 'Valentina'
    assert d['language'] == 'es' and 'checks' in d


# ════════════════════════════════════════════════════════════════════════════
# Sync (reparación)
# ════════════════════════════════════════════════════════════════════════════
def test_sync_creates_tool_resources_and_patches_tool_ids():
    fake = FakeEL(agent=agent_cfg(conversation_config__tts={'model_id': 'eleven_turbo_v2', 'voice_id': 'voz_es_1'},
                                  conversation_config__agent__prompt={'prompt': 'x', 'llm': 'gemini-2.0-flash'}))
    specs = SPECS()
    res = va.sync_agent(KEY, AGENT, server.BIXBY_SYSTEM_PROMPT, specs, http=fake)
    assert res['ok'] and res['mode'] == 'tool_ids', res
    posts = fake.by('POST', '/v1/convai/tools')
    assert len(posts) == len(specs) == res['tools_registered']
    for p in posts:
        tc = p['json']['tool_config']
        assert tc['type'] == 'client' and tc['name'] and tc['description'] and tc['expects_response'] is True
        assert 1 <= tc['response_timeout_secs'] <= 120
        if 'parameters' in tc:
            assert tc['parameters']['type'] == 'object' and tc['parameters']['properties']
            for k, prop in tc['parameters']['properties'].items():
                assert prop.get('description'), (tc['name'], k)
    brain = next(p['json']['tool_config'] for p in posts if p['json']['tool_config']['name'] == 'ask_khipu_brain')
    assert brain['response_timeout_secs'] == 60 and brain['parameters']['required'] == ['question']
    patch = fake.by('PATCH', f'/v1/convai/agents/{AGENT}')[0]['json']
    pr = patch['conversation_config']['agent']['prompt']
    assert 'tools' not in pr and len(pr['tool_ids']) == len(specs)       # NUNCA tools en línea + tool_ids
    assert pr['prompt'] == server.BIXBY_SYSTEM_PROMPT
    assert pr['llm'] == va.LLM_DEFAULT and res['llm_fixed']['from'] == 'gemini-2.0-flash'
    assert patch['conversation_config']['agent']['language'] == 'es'
    assert patch['conversation_config']['tts'] == {'model_id': 'eleven_flash_v2_5', 'voice_id': 'voz_es_1'}
    ev = patch['conversation_config']['conversation']['client_events']
    assert 'client_tool_call' in ev and 'ping' in ev and ev[:4] == ['audio', 'interruption', 'user_transcript', 'agent_response']
    assert 'platform_settings' not in patch                       # sin ELEVENLABS_ALLOW_OVERRIDE no toca overrides


def test_sync_is_idempotent_and_reuses_tools_by_name():
    fake = FakeEL()
    va.sync_agent(KEY, AGENT, server.BIXBY_SYSTEM_PROMPT, SPECS(), http=fake)
    n_tools = len(fake.tools)
    fake.calls.clear()
    res = va.sync_agent(KEY, AGENT, server.BIXBY_SYSTEM_PROMPT, SPECS(), http=fake)
    assert res['ok'] and not res['tools_created'] and not res['tools_updated']
    assert not fake.by('POST', '/v1/convai/tools') and len(fake.tools) == n_tools
    # cambió UNA descripción → solo esa herramienta se actualiza (PATCH del recurso)
    specs = SPECS()
    specs[0]['description'] += ' (v2)'
    fake.calls.clear()
    res = va.sync_agent(KEY, AGENT, server.BIXBY_SYSTEM_PROMPT, specs, http=fake)
    assert res['tools_updated'] == [specs[0]['name']] and not fake.by('POST', '/v1/convai/tools')


def test_sync_keeps_owner_tools_and_migrated_tools():
    """ElevenLabs migró las viejas herramientas en línea a recursos: se reusan;
    las del dueño (webhooks) se conservan en tool_ids."""
    specs = SPECS()
    migrated = {'mig_1': va.tool_payload(specs[0]), 'own_webhook': {'type': 'webhook', 'name': 'crm_lookup'}}
    fake = FakeEL(tools=migrated,
                  agent=agent_cfg(conversation_config__agent__prompt={'prompt': 'x', 'tool_ids': ['mig_1', 'own_webhook']}))
    res = va.sync_agent(KEY, AGENT, server.BIXBY_SYSTEM_PROMPT, specs, http=fake)
    ids = fake.agent['conversation_config']['agent']['prompt']['tool_ids']
    assert res['ok'] and 'mig_1' in ids and 'own_webhook' in ids and len(ids) == len(specs) + 1
    assert specs[0]['name'] not in res['tools_created']


def test_sync_does_not_downgrade_modern_tts_and_enables_overrides_with_env(monkeypatch):
    monkeypatch.setenv('ELEVENLABS_ALLOW_OVERRIDE', '1')
    fake = FakeEL(agent=agent_cfg(conversation_config__tts={'model_id': 'eleven_v4', 'voice_id': 'v9'}))
    res = va.sync_agent(KEY, AGENT, 'p', SPECS(), http=fake, allow_overrides=va.override_env_on())
    patch = fake.by('PATCH', f'/v1/convai/agents/{AGENT}')[0]['json']
    assert 'tts' not in patch['conversation_config'] and res['tts_fixed'] is False
    ov = patch['platform_settings']['overrides']['conversation_config_override']['agent']
    assert ov == {'language': True, 'first_message': True} and res['overrides_enabled']
    assert fake.agent['conversation_config']['tts']['model_id'] == 'eleven_v4'


def test_sync_falls_back_when_tool_ids_rejected():
    fake = FakeEL(fail={('PATCH', f'/v1/convai/agents/{AGENT}'): [
        R(422, {'detail': [{'loc': ['body', 'tool_ids'], 'msg': 'bad'}]}),
        R(422, {'detail': [{'loc': ['body', 'tools'], 'msg': 'tools deprecated'}]}),
    ]})
    res = va.sync_agent(KEY, AGENT, 'p', SPECS(), http=fake)
    assert res['ok'] and res['mode'] == 'prompt_only' and res['fallback_reason']
    bodies = [c['json'] for c in fake.by('PATCH', f'/v1/convai/agents/{AGENT}')]
    assert 'tool_ids' in bodies[0]['conversation_config']['agent']['prompt']
    assert 'tools' in bodies[1]['conversation_config']['agent']['prompt']
    assert set(bodies[2]['conversation_config']['agent']['prompt']) == {'prompt'}


def test_sync_reports_bad_key_without_writing():
    fake = FakeEL(fail={('GET', f'/v1/convai/agents/{AGENT}'): R(401, {'detail': {'status': 'invalid_api_key'}})})
    res = va.sync_agent(KEY, AGENT, 'p', SPECS(), http=fake)
    assert not res['ok'] and res['code'] == 'invalid_api_key' and res['fix_es'] and res['error_en']
    assert not [c for c in fake.calls if c['method'] in ('POST', 'PATCH')]


def test_sync_route_uses_new_sync(client, el, monkeypatch):
    monkeypatch.setenv('TRADE_PIN', PIN)
    r = client.post('/api/voice/sync-agent', headers={'X-Trade-Pin': PIN, 'Content-Type': 'application/json'})
    d = r.get_json()
    assert r.status_code == 200 and d['ok'] and d['mode'] == 'tool_ids'
    assert d['tools_registered'] == len(SPECS())
    assert el.agent['conversation_config']['agent']['prompt']['prompt'] == server.BIXBY_SYSTEM_PROMPT


def test_tts_and_llm_rules():
    assert va.tts_fix_for('eleven_turbo_v2_5') == 'eleven_flash_v2_5'
    assert va.tts_fix_for('eleven_turbo_v2', 'es') == 'eleven_flash_v2_5'
    assert va.tts_fix_for('eleven_turbo_v2', 'en') == 'eleven_flash_v2'
    assert va.tts_fix_for('eleven_flash_v2', 'es') == 'eleven_flash_v2_5'
    assert va.tts_fix_for('eleven_monolingual_v1') == 'eleven_flash_v2_5'
    assert va.tts_fix_for('') == 'eleven_flash_v2_5'
    for ok in ('eleven_flash_v2_5', 'eleven_multilingual_v2', 'eleven_v3_conversational', 'eleven_v4', 'eleven_v4_turbo'):
        assert va.tts_fix_for(ok, 'es') is None, ok
    for old in ('gemini-1.5-flash', 'gemini-2.0-flash-001', 'claude-3-5-sonnet', 'gpt-3.5-turbo', 'gpt-4',
                'gemini-2.5-flash-preview-05-20', 'grok-beta'):
        assert va.llm_is_legacy(old), old
    for new in ('gemini-3.5-flash', 'claude-haiku-4-5', 'gpt-5.4-mini', 'gemini-2.5-flash', ''):
        assert not va.llm_is_legacy(new), new


# ════════════════════════════════════════════════════════════════════════════
# agent-tune / bixby-prompt
# ════════════════════════════════════════════════════════════════════════════
def test_agent_tune_validates_models(client, el, monkeypatch):
    monkeypatch.setenv('TRADE_PIN', PIN)
    monkeypatch.setenv('ELEVENLABS_ALLOW_OVERRIDE', 'yes')
    h = {'X-Trade-Pin': PIN, 'Content-Type': 'application/json'}
    for bad in ('eleven_turbo_v2_5', 'eleven_v3', 'gpt-4'):
        r = client.post('/api/voice/agent-tune', data=json.dumps({'tts_model': bad}), headers=h)
        assert r.status_code == 400 and 'eleven_v4' in r.get_json()['valid'], bad
    assert client.post('/api/voice/agent-tune', data=json.dumps({'voice_id': '../x'}), headers=h).status_code == 400
    r = client.post('/api/voice/agent-tune', data=json.dumps({'tts_model': 'eleven_v4', 'language': 'ES'}), headers=h)
    assert r.status_code == 200 and r.get_json()['ok']
    assert el.agent['conversation_config']['tts']['model_id'] == 'eleven_v4'
    assert el.agent['conversation_config']['agent']['language'] == 'es'


@pytest.mark.parametrize('val,expected', [('1', True), ('true', True), ('yes', True), ('TRUE', True),
                                          ('false', False), ('', False)])
def test_bixby_prompt_override_flag(client, monkeypatch, val, expected):
    monkeypatch.setenv('ELEVENLABS_ALLOW_OVERRIDE', val)
    d = client.get('/api/voice/bixby-prompt').get_json()
    assert d['allow_override'] is expected and len(d['system_prompt']) > 200


# ════════════════════════════════════════════════════════════════════════════
# Espejo server ↔ voice.js
# ════════════════════════════════════════════════════════════════════════════
def test_tool_timeouts_and_cases_mirror_voice_js():
    js = open(os.path.join(ROOT, 'engine', 'voice.js'), encoding='utf-8').read()
    m = re.search(r'const VOICE_TOOL_TIMEOUT_S = \{(.*?)\};', js, re.S)
    js_map = dict((k, int(v)) for k, v in re.findall(r'(\w+):\s*(\d+)', m.group(1)))
    assert js_map == server._VOICE_TOOL_TIMEOUTS
    assert re.search(r'const VOICE_TOOL_TIMEOUT_DEFAULT_S = 10;', js)
    for t in SPECS():
        assert t['response_timeout_secs'] == server._VOICE_TOOL_TIMEOUTS.get(t['name'], 10)
        assert f"case '{t['name']}'" in js, f"voice.js no maneja la herramienta {t['name']}"
