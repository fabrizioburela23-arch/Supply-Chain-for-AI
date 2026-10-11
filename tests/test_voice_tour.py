"""Recorrido de un minuto para Khipus OS con la voz de Khipu (2026-10-11), lado servidor y guion.

El recorrido viejo hablaba de pestañas, decía "cuenta simulada" (falso si la cuenta del bróker es real) y,
sin voz premium, se leía con la voz robótica del navegador. Ahora:
  · UN guion (engine/tour_script.js) que leen el navegador (window.KHIPU_TOUR) y el servidor (core/tour.py);
  · con la conversación de voz abierta lo narra el agente (run_guided_demo start/next/stop);
  · sin conversación, cada frase suena con la MISMA voz del agente: GET /api/voice/tour/<lang>/<paso>
    (solo frases del guion, en caché; sin voz → 404 y la narración queda escrita).
Sin red: un ElevenLabs falso."""
import json
import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

import requests  # noqa: E402

import server  # noqa: E402
from core import tour  # noqa: E402
from core import voice_agent as va  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = 'sk_el_TEST_TOUR_KEY'
AGENT = 'agent_tour_1'
KINDS = {'empty', 'graph', 'glance', 'xray', 'sim', 'agents', 'insights', 'broker'}


# ── guion ────────────────────────────────────────────────────────────────────
def test_guion_es_json_estricto_y_bilingue():
    src = open(os.path.join(ROOT, 'engine', 'tour_script.js'), encoding='utf-8').read()
    body = re.search(r'\.KHIPU_TOUR\s*=\s*(\{.*\})\s*;\s*$', src, re.S).group(1)
    data = json.loads(body)
    assert data == tour.TOUR and 7 <= len(tour.STEPS) <= 12
    ids = [s['id'] for s in tour.STEPS]
    assert len(set(ids)) == len(ids)
    for s in tour.STEPS:
        assert s['act']['kind'] in KINDS, s['id']
        if s['act']['kind'] in ('glance', 'xray', 'sim'):
            assert s['act'].get('company'), s['id']
        for lang in ('es', 'en'):
            t = s[lang]
            assert 20 <= len(t) <= 200, (s['id'], lang)
            assert not re.search(r'[\[\]{}<>_@]', t), (s['id'], lang)          # nada técnico que la voz lea


def test_guion_dura_cerca_de_un_minuto():
    for lang, cps in (('es', 15.0), ('en', 15.0)):          # ~15 caracteres por segundo hablados
        secs = sum(len(s[lang]) for s in tour.STEPS) / cps
        assert 45 <= secs <= 85, (lang, secs)


def test_guion_dice_la_verdad_y_nombra_a_todas_las_mascotas():
    from core.agents_registry import AGENTS
    by = {s['id']: s for s in tour.STEPS}
    money = [s for s in tour.STEPS if s['act']['kind'] == 'broker']
    assert money, 'el recorrido muestra Mi cuenta'
    for s in money:
        assert 'dinero real' in s['es'] and 'real money' in s['en']             # práctica O real, nunca "simulada" fija
        assert 'confirmación' in s['es'] and 'confirmation' in s['en']
    for s in tour.STEPS:
        assert 'simulada' not in s['es'] and 'simulated account' not in s['en']
    agents = [s for s in tour.STEPS if s['act']['kind'] == 'agents']
    assert agents
    for a in AGENTS:
        if a['id'] == 'khipu':
            continue
        assert a['es'] in agents[0]['es'] and a['en'] in agents[0]['en'], a['id']
    sim = [s for s in tour.STEPS if s['act']['kind'] == 'sim'][0]
    assert 'hipotético' in sim['es'] and 'hypothetical' in sim['en']
    assert by[tour.STEPS[0]['id']]['act']['kind'] == 'empty'


def test_empresas_del_guion_existen_en_el_catalogo():
    snap = json.load(open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8'))
    names = {str(n.get(k) or '').lower() for n in snap['nodes'] for k in ('id', 'label', 'mkt')}
    for s in tour.STEPS:
        c = s['act'].get('company')
        if c:
            assert c.lower() in names, c


def test_el_navegador_carga_el_guion_antes_que_la_cabina():
    html = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    i = html.index('<script src="engine/tour_script.js"></script>')
    assert i < html.index('<script src="engine/cockpit.js"></script>')
    assert i < html.index('<script src="engine/voice.js"></script>')
    assert "'/engine/tour_script.js'" in open(os.path.join(ROOT, 'sw.js'), encoding='utf-8').read()
    r = subprocess.run(['node', '-e', "require('./engine/tour_script.js'); "
                        "process.stdout.write(JSON.stringify(globalThis.KHIPU_TOUR))"],
                       cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == tour.TOUR


def test_line_valida_paso_e_idioma():
    assert tour.line(0, 'es') == tour.STEPS[0]['es']
    assert tour.line(len(tour.STEPS), 'es') is None and tour.line(-1, 'en') is None
    assert tour.line(0, 'fr') is None and tour.line('1', 'es') is None


# ── voz: herramienta y modelos ───────────────────────────────────────────────
def test_herramienta_del_recorrido():
    spec = {t['name']: t for t in server._bixby_client_tools()}['run_guided_demo']
    assert spec['parameters']['properties']['action']['enum'] == ['start', 'next', 'stop']
    assert spec['parameters']['required'] == [] and spec['response_timeout_secs'] == 30
    d = spec['description']
    assert 'EXPLICITLY' in d and 'NEVER at session start' in d and 'EXACTLY' in d and 'done:true' in d
    p = server.BIXBY_SYSTEM_PROMPT
    assert '## THE ONE-MINUTE TOUR' in p and 'stopped:true' in p
    assert 'STAY QUIET' not in d                                     # antes se callaba: ahora narra con su voz


def test_modelos_del_audio():
    assert va.tour_tts_models('eleven_v4', 'es') == ['eleven_v4', 'eleven_multilingual_v2', 'eleven_flash_v2_5']
    assert va.tour_tts_models('eleven_flash_v2', 'es') == ['eleven_multilingual_v2', 'eleven_flash_v2_5']   # solo inglés
    assert va.tour_tts_models('eleven_turbo_v2_5', 'en')[0] == 'eleven_flash_v2_5'                       # deprecado
    assert va.tour_tts_models(None, 'es') == list(va.TOUR_TTS_FALLBACKS)


# ── endpoint de audio ────────────────────────────────────────────────────────
class _R:
    def __init__(self, status, payload=None, content=b''):
        self.status_code, self._p, self.content = status, payload, content
        self.text = json.dumps(payload) if payload is not None else ''

    def json(self):
        if self._p is None:
            raise ValueError('no json')
        return self._p


class FakeEL:
    def __init__(self, tts_model='eleven_v4', voice='voz_khipu_1', reject_models=(), fail=None):
        self.tts_model, self.voice, self.reject, self.fail = tts_model, voice, set(reject_models), fail
        self.posts = []

    def get(self, url, params=None, headers=None, timeout=None, **_):
        assert headers.get('xi-api-key') == KEY
        if url.endswith(f'/v1/convai/agents/{AGENT}'):
            return _R(200, {'agent_id': AGENT, 'conversation_config': {
                'tts': {'model_id': self.tts_model, 'voice_id': self.voice}, 'agent': {'prompt': {}}}})
        return _R(404, {'detail': 'Not Found'})

    def post(self, url, params=None, json=None, headers=None, timeout=None, **_):
        assert url.startswith('https://api.elevenlabs.io/v1/text-to-speech/')
        assert headers.get('xi-api-key') == KEY and params == {'output_format': 'mp3_44100_128'}
        self.posts.append({'voice': url.rsplit('/', 1)[1], **json})
        if self.fail:
            return self.fail
        if json['model_id'] in self.reject:
            return _R(422, {'detail': {'status': 'invalid_model', 'message': 'model not allowed'}})
        return _R(200, content=b'ID3-fake-mp3-' + json['model_id'].encode())


@pytest.fixture
def client(monkeypatch):
    from core import http as core_http
    monkeypatch.setattr(core_http, '_rate_limit', lambda *a, **k: True)
    server._TOUR_AUDIO.clear()
    va.forget_agent()
    server.app.config['TESTING'] = True
    yield server.app.test_client()
    server._TOUR_AUDIO.clear()
    va.forget_agent()


def _wire(monkeypatch, fake):
    monkeypatch.setattr(requests, 'get', fake.get)
    monkeypatch.setattr(requests, 'post', fake.post)
    monkeypatch.setattr(server, 'ELEVENLABS_KEY', KEY)
    monkeypatch.setattr(server, 'ELEVENLABS_AGENT_ID', AGENT)


def test_audio_con_la_voz_del_agente_y_en_cache(client, monkeypatch):
    fake = FakeEL()
    _wire(monkeypatch, fake)
    r = client.get('/api/voice/tour/es/0')
    assert r.status_code == 200 and r.mimetype == 'audio/mpeg' and r.data.startswith(b'ID3')
    assert fake.posts == [{'voice': 'voz_khipu_1', 'text': tour.STEPS[0]['es'], 'model_id': 'eleven_v4'}]
    assert r.headers['X-Tour-Model'] == 'eleven_v4' and 'max-age' in r.headers['Cache-Control']
    r2 = client.get('/api/voice/tour/es/0')
    assert r2.status_code == 200 and r2.data == r.data and len(fake.posts) == 1     # caché: no se paga dos veces
    client.get(f'/api/voice/tour/en/{len(tour.STEPS) - 1}')
    assert fake.posts[-1]['text'] == tour.STEPS[-1]['en']


def test_modelo_rechazado_pasa_al_siguiente(client, monkeypatch):
    fake = FakeEL(reject_models={'eleven_v4'})
    _wire(monkeypatch, fake)
    r = client.get('/api/voice/tour/en/1')
    assert r.status_code == 200 and r.headers['X-Tour-Model'] == 'eleven_multilingual_v2'
    assert [p['model_id'] for p in fake.posts] == ['eleven_v4', 'eleven_multilingual_v2']


def test_cuota_agotada_no_reintenta_y_responde_claro(client, monkeypatch):
    fake = FakeEL(fail=_R(401, {'detail': {'status': 'quota_exceeded', 'message': 'quota exceeded'}}))
    _wire(monkeypatch, fake)
    r = client.get('/api/voice/tour/es/2')
    d = r.get_json()
    assert r.status_code == 402 and d['code'] == 'quota_exceeded' and d['error'] and d['error_en']
    assert len(fake.posts) == 1 and KEY not in r.get_data(as_text=True)


def test_sin_voz_configurada_o_paso_invalido(client, monkeypatch):
    monkeypatch.setattr(server, 'ELEVENLABS_KEY', '')
    r = client.get('/api/voice/tour/es/0')
    assert r.status_code == 404 and r.get_json()['code'] == 'not_configured' and r.get_json()['error_en']
    _wire(monkeypatch, FakeEL())
    assert client.get(f'/api/voice/tour/es/{len(tour.STEPS)}').status_code == 404
    assert client.get('/api/voice/tour/fr/0').status_code == 400
    assert client.get('/api/voice/tour/es/abc').status_code == 404


def test_solo_frases_del_guion():
    """No hay forma de pedir texto libre: la ruta solo acepta idioma + número de paso."""
    rules = [r for r in server.app.url_map.iter_rules() if r.rule.startswith('/api/voice/tour')]
    assert [r.rule for r in rules] == ['/api/voice/tour/<lang>/<int:step>'] and rules[0].methods >= {'GET'}
    assert 'POST' not in rules[0].methods
    assert 'api.elevenlabs.io' not in open(os.path.join(ROOT, 'server.py'), encoding='utf-8').read()
