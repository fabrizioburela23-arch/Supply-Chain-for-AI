"""Overnight 2026-10-10 — arreglos de la revisión (fixer). Cada test fallaba antes del arreglo.

UI:   riesgo en celular sin desborde lateral (botones largos envuelven) · «?» de explainChip con el acento del tema
      en el reporte de riesgo y en Carteras.
IA:   🩺 hace ping a Claude con el pensamiento que CADA modelo acepta (Sonnet 5.5 rechaza 'disabled') ·
      el presupuesto de research cuenta los tokens REALES (incluido el pensamiento) · /api/ai/debug muestra el
      orden efectivo · /api/research/deep sin IA responde en el idioma de quien pregunta.
Chat: plazo PROPIO del cliente (la voz espera 55 s) → la respuesta profunda nunca llega después del corte.
Voz:  el sync no parchea con un agente que no pudo leer · respeta modelos TTS desconocidos (más nuevos) ·
      no duplica herramientas si no puede listarlas · pide agent_tool_response · al colgar deja terminar la
      despedida · /api/voice/agent-diag con límite y sin datos de facturación.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import time
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

import requests  # noqa: E402

import server  # noqa: E402
from core import ai  # noqa: E402
from core import ai_usage  # noqa: E402
from core import khipu_chat as kc  # noqa: E402
from core import voice_agent as va  # noqa: E402
from research import llm as rllm  # noqa: E402
from tests import test_overnight_voice_server as vs  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')


def _r(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


@pytest.fixture
def client():
    server.app.config['TESTING'] = True
    return server.app.test_client()


@pytest.fixture(autouse=True)
def _limpio(monkeypatch):
    va.forget_agent()
    monkeypatch.setattr(va, '_sleep', lambda s: None)
    monkeypatch.setattr(ai, '_CIRCUIT', {})
    monkeypatch.setattr(ai_usage, '_ensure_writer', lambda: None)
    from core import http as core_http
    monkeypatch.setattr(core_http, '_rate_limit', lambda *a, **k: True)
    yield
    va.forget_agent()


# ════════════════════════════════════════════════════════════════════════════
# UI
# ════════════════════════════════════════════════════════════════════════════
def _media_block(js, q):
    i = js.index("'@media(max-width:" + q + "px){")
    return js[i:js.index("'@media", i + 10)]


def test_riesgo_celular_botones_largos_envuelven():
    js = _r('engine/riskreport.js')
    mob = _media_block(js, '760')
    assert '#krr .btn{white-space:normal;height:auto;min-height:40px;max-width:100%' in mob
    assert '#krr .btn.big{height:auto' in mob             # el grande no queda con alto fijo y texto envuelto


def test_chips_de_ayuda_con_el_acento_del_tema():
    for rel, root in (('engine/riskreport.js', '#krr'), ('engine/portfolios.js', '.kpf-root')):
        js = _r(rel)
        rule = root + ' span[onclick*="explainMetric"]{color:var(--os-accent,#4C8DF6)!important'
        assert rule in js, rel


def test_khipu_chat_js_manda_el_plazo_del_cliente():
    js = _r('engine/khipu_chat.js')
    assert 'body.deadline_s = Math.round(opts.timeout / 1000)' in js
    assert "window.KhipuChat.send(q, { timeout: 55000 })" in _r('engine/voice.js')


# ════════════════════════════════════════════════════════════════════════════
# 🩺 Claude: ping con el pensamiento que acepta cada modelo
# ════════════════════════════════════════════════════════════════════════════
class _FakeAnthropic400(Exception):
    status_code = 400


def _fake_anthropic(sent):
    class Messages:
        def create(self, **kw):
            sent.append(kw)
            fam, _ver = ai._claude_version(kw['model'])
            th = (kw.get('thinking') or {}).get('type')
            if th == 'disabled' and ai.claude_thinking_mode(kw['model']) in ('between_tools', 'always'):
                raise _FakeAnthropic400('Error code: 400 - thinking.type.disabled is not supported for this model')
            return types.SimpleNamespace(model=kw['model'], content=[], stop_reason='max_tokens', usage=None)

    class Client:
        def __init__(self, **kw):
            self.messages = Messages()
    return types.SimpleNamespace(Anthropic=Client, APITimeoutError=TimeoutError, APIConnectionError=ConnectionError)


def test_diag_claude_sonnet55_y_haiku_en_verde(monkeypatch):
    sent = []
    monkeypatch.setitem(sys.modules, 'anthropic', _fake_anthropic(sent))
    monkeypatch.setattr(server, 'CLAUDE', 'sk-ant-test')
    import core.config as cfg
    monkeypatch.setattr(cfg, 'AI_MODEL_FAST', 'claude-haiku-4-5')
    monkeypatch.setattr(cfg, 'AI_MODEL_DEEP', 'claude-sonnet-5-5')
    d = server._diag_claude()
    assert d['ok'] and '✗' not in d['detail'], d['detail']
    by_model = {k['model']: k.get('thinking') for k in sent}
    assert by_model['claude-haiku-4-5'] == {'type': 'disabled'}
    assert by_model['claude-sonnet-5-5'] == {'type': 'between_tools'}
    # Opus 5.5 / Fable: sin `thinking` (no se puede apagar)
    sent.clear()
    monkeypatch.setattr(cfg, 'AI_MODEL_DEEP', 'claude-opus-5-5')
    assert server._diag_claude()['ok'] and 'thinking' not in [k for k in sent if k['model'] == 'claude-opus-5-5'][0]


# ════════════════════════════════════════════════════════════════════════════
# Presupuesto de research = tokens REALES del proveedor
# ════════════════════════════════════════════════════════════════════════════
class _Schema:
    @staticmethod
    def model_validate(d):
        if not isinstance(d, dict) or 'ok' not in d:
            raise ValueError('falta ok')
        return d


class _ThinkingProvider(rllm.LLMProvider):
    """Como Sonnet 5.5 en el nivel profundo: el texto visible es corto, el proveedor cobra 9.000 de salida."""
    name = 'thinking'

    def available(self):
        return True

    def generate(self, system, prompt, max_tokens=1500):
        ai_usage.record('claude', 'claude-sonnet-5-5', 1200, 9000)
        return '{"ok": true}', 'claude-sonnet-5-5'


def test_research_cuenta_el_pensamiento_que_cobra_el_proveedor():
    obj, meta = _ThinkingProvider().structured_generate('sys', 'prompt', _Schema)
    assert obj == {'ok': True}
    assert meta['tokens_in'] == 1200 and meta['tokens_out'] == 9000      # antes: len(texto)/4 ≈ 3
    assert rllm.estimate_cost(meta['model'], meta['tokens_in'], meta['tokens_out']) == pytest.approx(
        ai_usage.cost_of('claude', 'claude-sonnet-5-5', 1200, 9000))


def test_research_sin_registro_real_sigue_estimando():
    obj, meta = rllm.FakeProvider(['{"ok": 1}']).structured_generate('s', 'p', _Schema)
    assert meta['tokens_out'] == rllm.estimate_tokens('{"ok": 1}') and meta['tokens_in'] > 0


def test_medidor_es_por_hilo_y_anidable():
    with ai_usage.meter() as a:
        ai_usage.record('gemini', 'gemini-3.8-flash', 10, 20)
        with ai_usage.meter() as b:
            ai_usage.record('gemini', 'gemini-3.8-flash', 1, 2)
    ai_usage.record('gemini', 'gemini-3.8-flash', 100, 100)        # fuera: no cuenta
    assert (a['tokens_in'], a['tokens_out'], a['calls']) == (11, 22, 2)
    assert (b['tokens_in'], b['tokens_out'], b['calls']) == (1, 2, 1)


# ════════════════════════════════════════════════════════════════════════════
# /api/ai/debug y /api/research/deep
# ════════════════════════════════════════════════════════════════════════════
def test_ai_debug_muestra_el_orden_efectivo(client, monkeypatch):
    monkeypatch.setattr(ai, '_ai_complete', lambda *a, **k: ('{"ok":true}', 'fake'))
    monkeypatch.setattr(ai, '_complete_claude', lambda *a, **k: ('{"ok":true}', 'fake'))
    d = client.get('/api/ai/debug?tier=deep').get_json()
    assert d['ai_order'] == ai.provider_order('deep') and d['routing']['deep'] == ai.provider_order('deep')
    d = client.get('/api/ai/debug').get_json()
    assert d['ai_order'] == ai.provider_order('fast') and 'ai_order_env' in d


def test_research_deep_sin_ia_en_el_idioma_de_quien_pregunta(client, monkeypatch):
    monkeypatch.setattr(server, '_ai_configured', lambda: False)
    en = client.post('/api/research/deep', json={'id': 'nvidia', 'lang': 'en'})
    es = client.post('/api/research/deep', json={'id': 'nvidia', 'lang': 'es'})
    assert en.status_code == es.status_code == 400
    de, ds = en.get_json(), es.get_json()
    assert de['error'] == de['error_en'] and 'AI provider' in de['error']
    assert ds['error'] == ds['error_es'] and 'proveedor de IA' in ds['error'] and ds['error_en']


# ════════════════════════════════════════════════════════════════════════════
# Chat: plazo del cliente (voz = 55 s)
# ════════════════════════════════════════════════════════════════════════════
def test_validate_request_plazo_del_cliente():
    assert kc.validate_request({'message': 'hola'})['deadline_s'] is None
    assert kc.validate_request({'message': 'hola', 'deadline_s': 55})['deadline_s'] == 55
    assert kc.validate_request({'message': 'hola', 'deadline_s': 9999})['deadline_s'] == kc.CLIENT_DEADLINE_MAX_S
    assert kc.validate_request({'message': 'hola', 'deadline_s': 1})['deadline_s'] == kc.CLIENT_DEADLINE_MIN_S
    assert kc.validate_request({'message': 'hola', 'deadline_s': 'x'})['deadline_s'] is None


def test_techo_nunca_pasa_el_plazo_del_cliente():
    t0 = 1000.0
    assert kc._hard_end(t0, 45) == pytest.approx(t0 + 66)
    assert kc._hard_end(t0, 45, t0 + 51) == pytest.approx(t0 + 51)


def test_deep_final_respeta_el_plazo(monkeypatch):
    seen = []

    def fake_call(system, prompt, timeout, tier='fast'):
        seen.append(timeout)
        return json.dumps({'final': {'answer': 'Análisis profundo completo.', 'actions': []}}), 'fake:deep'
    monkeypatch.setattr(kc, '_call_ai', fake_call)
    now = time.monotonic()
    out = kc._deep_final('s', 'q', [], 'es', {}, [], '', now - 28, 45, None, cap=now + 23)
    assert out['called'] and seen[-1] <= 23.5                       # antes: hasta 30 s → la voz ya había cortado
    seen.clear()
    out = kc._deep_final('s', 'q', [], 'es', {}, [], '', now - 45, 45, None, cap=now + 5)
    assert not out['called'] and not seen                           # < DEEP_FINAL_MIN_S: queda la respuesta rápida


def _jev_ans(route):
    return {'route': {'choice': route, 'confidence': 0.9}, 'mentions_company': {'noul': 0.9},
            'asks_trade': {'noul': 0.0}, 'about_portfolio': {'noul': 0.0}, 'urgency': {'score': 1}}


def test_chat_de_voz_la_respuesta_profunda_cabe_en_55s(monkeypatch):
    from core import decide
    from mcp_server import tools as mt
    monkeypatch.setattr(mt, '_live_profile', lambda sym: {'available': False, 'reason': 'test (offline)'})
    monkeypatch.setattr(mt._auth, 'db_available', lambda: False)
    monkeypatch.setattr(decide, '_persist', lambda row: None)
    monkeypatch.setattr('core.live_facts.live_facts_block', lambda m: '')
    monkeypatch.setattr(ai, '_ai_configured', lambda: True)
    monkeypatch.setenv('TYPESAFE_API_KEY', 'ts-test')
    monkeypatch.delenv('DECIDE_CONTROL', raising=False)
    monkeypatch.setattr(decide, 'ask', lambda state, q, feature=None, timeout=None: _jev_ans('needs_deep_reasoning'))
    calls = []

    def fake_ai(system, prompt, max_tokens=1000, tier='fast', **kw):
        calls.append((tier, kw.get('timeout_s')))
        ans = 'Análisis profundo de la tesis de Nvidia.' if tier == 'deep' else 'Respuesta rápida.'
        return json.dumps({'final': {'answer': ans, 'actions': []}}), f'fake:{tier}'
    monkeypatch.setattr(ai, '_ai_complete', fake_ai)
    kc.run_chat('¿cuál es la tesis de Nvidia a 3 años?', [], 'es', {})
    free_deep = [t for tier, t in calls if tier == 'deep'][-1]
    calls.clear()
    out = kc.run_chat('¿cuál es la tesis de Nvidia a 3 años?', [], 'es', {}, deadline_s=20)
    voice_deep = [t for tier, t in calls if tier == 'deep'][-1]
    assert free_deep == pytest.approx(kc.DEEP_FINAL_TIMEOUT_S, abs=0.5)
    assert voice_deep <= 20 - kc.CLIENT_NET_MARGIN_S + 0.5 and out['answer'].startswith('Análisis profundo')


# ════════════════════════════════════════════════════════════════════════════
# Voz: sync seguro
# ════════════════════════════════════════════════════════════════════════════
def _owner_agent():
    return vs.agent_cfg(conversation_config__tts={'model_id': 'eleven_v4', 'voice_id': 'voz_es_1'},
                        conversation_config__agent__prompt={'prompt': 'x', 'llm': 'gemini-3.5-flash',
                                                            'tool_ids': ['owner_webhook_1']})


def test_sync_no_parchea_si_no_pudo_leer_el_agente():
    path = f'/v1/convai/agents/{vs.AGENT}'
    fake = vs.FakeEL(agent=_owner_agent(), tools={'owner_webhook_1': {'type': 'webhook', 'name': 'crm'}},
                     fail={('GET', path): [vs.R(503, {'detail': 'Internal server error'})] * 5})
    res = va.sync_agent(vs.KEY, vs.AGENT, 'PROMPT', vs.SPECS(), http=fake)
    assert res['ok'] is False and res['stage'] == 'read_agent' and res['code'] == 'server_error'
    assert not fake.by('PATCH', path) and not fake.by('POST', '/v1/convai/tools')   # ni bajó eleven_v4 ni duplicó


def test_sync_reintenta_un_tropiezo_pasajero_y_conserva_lo_del_dueno():
    path = f'/v1/convai/agents/{vs.AGENT}'
    fake = vs.FakeEL(agent=_owner_agent(), tools={'owner_webhook_1': {'type': 'webhook', 'name': 'crm'}},
                     fail={('GET', path): [vs.R(503, {'detail': 'Internal server error'})]})
    res = va.sync_agent(vs.KEY, vs.AGENT, 'PROMPT', vs.SPECS(), http=fake)
    assert res['ok'], res
    patch = fake.by('PATCH', path)[0]['json']['conversation_config']
    assert 'tts' not in patch                                      # eleven_v4 se queda
    assert 'owner_webhook_1' in patch['agent']['prompt']['tool_ids']


def test_tts_desconocido_se_respeta_y_el_diagnostico_avisa():
    assert va.tts_fix_for('eleven_v5_flash', 'es') is None
    assert va.tts_fix_for('eleven_multilingual_v1') == va.TTS_DEFAULT
    fake = vs.FakeEL(agent=vs.agent_cfg(conversation_config__tts={'model_id': 'eleven_v5_flash', 'voice_id': 'v1'}))
    va.sync_agent(vs.KEY, vs.AGENT, 'PROMPT', vs.SPECS(), http=fake)
    assert fake.agent['conversation_config']['tts']['model_id'] == 'eleven_v5_flash'
    d = va.diagnose(vs.KEY, vs.AGENT, http=fake, expected_tools=[s['name'] for s in vs.SPECS()], prompt='PROMPT',
                    full=True)
    tts = [c for c in d['checks'] if c['id'] == 'tts'][0]
    assert tts['level'] == 'warn' and 'eleven_v5_flash' in json.dumps(tts, ensure_ascii=False)


def test_sin_listado_de_herramientas_no_se_crean_a_ciegas():
    fake = vs.FakeEL(fail={('GET', '/v1/convai/tools'): vs.R(503, {'detail': 'down'})})
    res = va.ensure_tools(vs.KEY, fake, vs.SPECS(), [])
    assert res['ok'] is False and res['list_error'] and not fake.by('POST', '/v1/convai/tools')


def test_eventos_incluyen_agent_tool_response():
    assert 'agent_tool_response' in va.REQUIRED_CLIENT_EVENTS
    fake = vs.FakeEL()
    va.sync_agent(vs.KEY, vs.AGENT, 'PROMPT', vs.SPECS(), http=fake)
    ev = fake.agent['conversation_config']['conversation']['client_events']
    assert 'agent_tool_response' in ev and 'client_tool_call' in ev


def test_agent_diag_sin_facturacion_y_con_limite(client, monkeypatch):
    fake = vs.FakeEL()
    monkeypatch.setattr(requests, 'get', fake.get)
    monkeypatch.setattr(server, 'ELEVENLABS_KEY', vs.KEY)
    monkeypatch.setattr(server, 'ELEVENLABS_AGENT_ID', vs.AGENT)
    d = client.get('/api/voice/agent-diag').get_json()
    assert 'subscription' not in d and 'checks' in d and vs.KEY not in json.dumps(d)
    assert getattr(server.voice_agent_diag, '__wrapped__', None) is not None      # pasa por rate_limit


# ════════════════════════════════════════════════════════════════════════════
# voice.js: al colgar (cierre limpio) la despedida termina de sonar
# ════════════════════════════════════════════════════════════════════════════
CLOSE_MAIN = r"""
async function main() {
  const R = {};
  const sess = { data: { signed_url: 'wss://api.elevenlabs.io/v1/convai/conversation?agent_id=a&conversation_signature=s',
    overrides: {}, language: 'es', override_env: false } };
  for (const [name, code] of [['clean', 1000], ['dropped', 1011]]) {
    const E = makeEnv({ session: sess });
    await E.V.connect();
    const ws = E.sockets[0];
    ws._open();
    ws._msg(META('pcm_24000', 'pcm_16000'));
    ws._msg({ type: 'audio', audio_event: { audio_base_64: b64pcm(new Array(48000).fill(500)), event_id: 3 } });   // 2 s
    const srcs = E.ctxs[0].sources.slice();
    ws._close(code, '');
    R[name] = { stoppedAtClose: srcs.some(s => s.stopped) };
    await E.advance(1000);
    R[name].stoppedAt1s = srcs.some(s => s.stopped);
    await E.advance(3000);
    R[name].stoppedAt4s = srcs.every(s => s.stopped);
    R[name].connected = E.V.isConnected;
    R[name].errors = E.errors;
  }
  process.stdout.write(JSON.stringify(R));
  process.exit(0);
}
main().catch(e => { process.stdout.write(JSON.stringify({ fatal: String(e && e.stack || e) })); process.exit(0); });
"""


@pytest.mark.skipif(not NODE, reason='node no instalado')
def test_cierre_limpio_deja_terminar_la_despedida():
    from tests import test_overnight_voice_client as vc
    harness = vc.HARNESS.split('async function main()')[0] + CLOSE_MAIN
    p = subprocess.run([NODE, '-e', harness, os.path.join(ROOT, 'engine', 'voice.js')],
                       capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr[-2000:]
    R = json.loads(p.stdout)
    assert 'fatal' not in R, R.get('fatal')
    assert R['clean'] == {'stoppedAtClose': False, 'stoppedAt1s': False, 'stoppedAt4s': True,
                          'connected': False, 'errors': []}, R['clean']
    assert R['dropped']['stoppedAtClose'] is True                   # caída de verdad: se corta al instante
