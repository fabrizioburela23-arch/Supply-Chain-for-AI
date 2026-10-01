"""tests/test_infra.py — endurecimiento de infraestructura (auditoría estructural
2026-09-30, grupo INFRA): #1 Dockerfile/exec, #2 hambre de hilos (IA + base),
#6 REMIGRATE_ON_BOOT seguro, #13 secretos de IA, #16 railway.toml, #17 motor de
matrices acotado, #19 versiones fijadas, #20 escrituras de ontología con PIN,
#22 aprobación atómica de propuestas.

Los tests SIN base corren siempre. Los que tocan Postgres se auto-saltan sin
DATABASE_URL (mismo patrón que test_ontology.py):
    DATABASE_URL=postgresql://postgres:devpass@localhost:5432/khipus_s3 pytest tests/test_infra.py -q
"""
import os
import re
import subprocess
import sys
import threading
import time
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')

PIN = 'pin-de-prueba-9137'


def _read(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as fh:
        return fh.read()


# ════════════════════════════════════════════════════════════════════════════
# #1 · #16 · #19 — Dockerfile, railway.toml, versiones fijadas
# ════════════════════════════════════════════════════════════════════════════

def test_dockerfile_exec_gunicorn_un_worker_y_apagado_ordenado():
    df = _read('Dockerfile')
    cmd = [ln for ln in df.splitlines() if ln.startswith('CMD')]
    assert len(cmd) == 1
    c = cmd[0]
    # exec → gunicorn es PID 1 y recibe el SIGTERM de Railway
    assert '"exec gunicorn' in c
    assert '--workers 1 ' in c, 'NO subir workers: el estado en memoria divergiría'
    # graceful-timeout < drainingSeconds de Railway (margen ≥ 5 s): si fueran
    # iguales, una orden que termina justo en el límite competía con el SIGKILL
    m = re.search(r'--graceful-timeout (\d+)', c)
    assert m, c
    # drainingSeconds se quitó de railway.toml (no verificado en el esquema de
    # Railway); el default de Railway deja ~30 s: graceful-timeout ≤ 25
    assert 0 < int(m.group(1)) <= 25, m.group(1)
    # reciclaje de worker APAGADO por defecto (borraría agente/rate limits/bloqueo del PIN)
    assert '${GUNICORN_MAX_REQUESTS:-0}' in c
    assert 'pip install --no-cache-dir -r requirements.txt -c constraints.txt' in df
    assert 'COPY requirements.txt constraints.txt' in df


def test_railway_reinicia_siempre_y_drena():
    import tomllib
    with open(os.path.join(ROOT, 'railway.toml'), 'rb') as fh:
        cfg = tomllib.load(fh)
    dep = cfg['deploy']
    assert dep['restartPolicyType'] == 'ALWAYS'
    assert 'restartPolicyMaxRetries' not in dep   # con 3 reintentos quedaba caído
    assert dep['healthcheckPath'] == '/api/health'
    assert 'drainingSeconds' not in dep   # no verificado en el esquema de Railway


def _req_names():
    names = []
    for ln in _read('requirements.txt').splitlines():
        ln = ln.split('#', 1)[0].strip()
        if not ln:
            continue
        m = re.match(r'^([A-Za-z0-9_.\-]+)', ln)
        names.append(m.group(1))
    return names


def _pins():
    pins = {}
    for ln in _read('constraints.txt').splitlines():
        ln = ln.split('#', 1)[0].strip()
        if not ln:
            continue
        m = re.match(r'^([A-Za-z0-9_.\-]+)==([A-Za-z0-9_.\-+]+)$', ln)
        assert m, f'línea de constraints no es un pin exacto: {ln!r}'
        pins[re.sub(r'[-_.]+', '-', m.group(1)).lower()] = m.group(2)
    return pins


def test_constraints_fija_cada_requirement_con_version_exacta():
    pins = _pins()
    faltan = [n for n in _req_names() if re.sub(r'[-_.]+', '-', n).lower() not in pins]
    assert not faltan, f'requirements sin versión fijada en constraints.txt: {faltan}'
    # la lección de 2026-09-28: SQLAlchemy 2.1 rompe la ontología (psycopg 3)
    major, minor = (int(x) for x in pins['sqlalchemy'].split('.')[:2])
    assert (major, minor) < (2, 1)
    # dependencias transitivas críticas también fijadas
    for dep in ('werkzeug', 'jinja2', 'itsdangerous', 'click', 'blinker', 'urllib3', 'certifi',
                'charset-normalizer', 'idna', 'anyio', 'pydantic-core', 'typing-extensions', 'cffi'):
        assert dep in pins, f'{dep} sin fijar'


def test_dockerignore_excluye_secretos_git_y_tests():
    lines = {ln.strip() for ln in _read('.dockerignore').splitlines() if ln.strip() and not ln.startswith('#')}
    for must in ('.git', '.env', 'tests', '**/__pycache__', '**/*.pyc', 'node_modules'):
        assert must in lines, f'.dockerignore no excluye {must}'


# ════════════════════════════════════════════════════════════════════════════
# #13 — la key de Gemini viaja en cabecera; los errores salen redactados
# ════════════════════════════════════════════════════════════════════════════

class _Resp:
    def __init__(self, status=200, data=None):
        self.status_code = status
        self.ok = 200 <= status < 300
        self._data = data if data is not None else {}

    def json(self):
        return self._data


def test_gemini_key_en_cabecera_nunca_en_la_url(monkeypatch):
    from core import ai
    key = 'AIzaSy-SECRETO-de-prueba-123456'
    monkeypatch.setattr(ai, 'GEMINI_KEY', key)
    seen = {}

    def fake_post(url, json=None, timeout=None, headers=None, **kw):  # noqa: A002
        seen.update(url=url, headers=headers or {})
        return _Resp(200, {'candidates': [{'content': {'parts': [{'text': 'hola'}]}}]})

    monkeypatch.setattr(ai.requests, 'post', fake_post)
    text, used = ai._complete_gemini('', 'ping', 5)
    assert text == 'hola' and used.startswith('gemini:')
    assert key not in seen['url'] and 'key=' not in seen['url']
    assert seen['headers'].get('x-goog-api-key') == key


def test_gemini_error_de_red_no_filtra_la_key(monkeypatch):
    import requests
    from core import ai
    key = 'AIzaSy-SECRETO-de-prueba-654321'
    monkeypatch.setattr(ai, 'GEMINI_KEY', key)

    def boom(url, **kw):
        raise requests.exceptions.ConnectionError(f'Max retries exceeded with url: {url}?key={key}')

    monkeypatch.setattr(ai.requests, 'post', boom)
    with pytest.raises(RuntimeError) as ei:
        ai._complete_gemini('', 'ping', 5)
    assert key not in str(ei.value)


def test_gemini_http_error_solo_codigo_y_estado(monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: _Resp(
        404, {'error': {'status': 'NOT_FOUND', 'message': 'models/x is not found; echo k-123456789'}}))
    with pytest.raises(RuntimeError) as ei:
        ai._complete_gemini('', 'ping', 5)
    msg = str(ei.value)
    assert msg == 'Gemini HTTP 404 NOT_FOUND'     # _ai_error_hint del 🩺 sigue viendo el 404


def test_cascada_redacta_secretos_de_los_proveedores(monkeypatch):
    from core import ai
    secret = 'sk-ant-SECRETO-ABCDEFGHIJ'
    monkeypatch.setattr(ai, 'CLAUDE', '')
    monkeypatch.setattr(ai, 'AI_ORDER', ['gemini', 'nvidia'])

    def leaky(*a, **k):
        raise RuntimeError(f'fallo llamando https://x.test/v1?token=abcdef123456&api_key={secret}')

    monkeypatch.setitem(ai._AI_PROVIDERS, 'gemini', (lambda: True, leaky))
    monkeypatch.setitem(ai._AI_PROVIDERS, 'nvidia', (lambda: True, leaky))
    with pytest.raises(RuntimeError) as ei:
        ai._ai_complete_raw('s', 'p', 10)
    msg = str(ei.value)
    assert 'Ningún proveedor' in msg
    assert secret not in msg and 'abcdef123456' not in msg


# ════════════════════════════════════════════════════════════════════════════
# #2 — la IA no puede dejar al servidor sin hilos
# ════════════════════════════════════════════════════════════════════════════

class _FakeMsg:
    def __init__(self, text, model='claude-test'):
        self.content = [type('B', (), {'type': 'text', 'text': text})()]
        self.model = model


def test_cliente_claude_timeout_corto_sin_reintentos_del_sdk(monkeypatch):
    import anthropic
    from core import ai
    made = []

    class FakeClient:
        def __init__(self, **kw):
            made.append(kw)
            self.messages = self

        def create(self, **kw):
            return _FakeMsg('ok')

    monkeypatch.setattr(ai, 'CLAUDE', 'sk-test-123456')
    monkeypatch.setattr(anthropic, 'Anthropic', FakeClient)
    assert ai._complete_claude('s', 'p', 10)[0] == 'ok'
    assert ai._complete_claude('s', 'p', 10, tier='deep')[0] == 'ok'
    # sin reintentos del SDK (reintentaba también los TIMEOUTS → cuelgue doble)
    assert made[0]['max_retries'] == 0 and made[0]['timeout'] <= 60
    assert made[1]['timeout'] <= 120          # deep: más margen, pero < --timeout 120 de gunicorn


def test_claude_timeout_no_prueba_otros_modelos(monkeypatch):
    """Un timeout de red no se arregla con OTRO modelo Claude: se sale al toque
    para que la cascada pase a Gemini/NVIDIA (antes: hasta 8 llamadas colgadas)."""
    import anthropic
    from core import ai

    class FakeTimeout(Exception):
        pass

    calls = []

    class FakeClient:
        def __init__(self, **kw):
            self.messages = self

        def create(self, **kw):
            calls.append(kw['model'])
            raise FakeTimeout('read timed out')

    monkeypatch.setattr(ai, 'CLAUDE', 'sk-test-123456')
    monkeypatch.setattr(anthropic, 'Anthropic', FakeClient)
    monkeypatch.setattr(anthropic, 'APITimeoutError', FakeTimeout)
    with pytest.raises(RuntimeError):
        ai._complete_claude('s', 'p', 10, model='claude-a')
    assert len(calls) == 1


def test_semaforo_ia_rechaza_en_vez_de_colgar(monkeypatch):
    import threading as _th
    from core import ai
    monkeypatch.setattr(ai, '_AI_SEM', _th.BoundedSemaphore(1))
    monkeypatch.setattr(ai, 'AI_BUSY_WAIT_S', 0.2)
    monkeypatch.setattr(ai, 'CLAUDE', '')
    monkeypatch.setattr(ai, 'AI_ORDER', ['gemini'])
    called = []
    monkeypatch.setitem(ai._AI_PROVIDERS, 'gemini', (lambda: True, lambda *a, **k: called.append(1) or ('x', 'g')))

    holding, release = _th.Event(), _th.Event()

    def hog():
        with ai._ai_slot():
            holding.set()
            release.wait(5)

    t = _th.Thread(target=hog)
    t.start()
    assert holding.wait(5)
    t0 = time.time()
    try:
        with pytest.raises(ai.AIBusyError) as ei:
            ai._ai_complete_raw('s', 'p', 10)
        assert time.time() - t0 < 3
        assert 'IA ocupada' in str(ei.value) and 'AI busy' in str(ei.value)
        assert not called                       # ni siquiera se intentó el proveedor
    finally:
        release.set()
        t.join(5)
    # liberado el cupo, la llamada normal funciona (y el semáforo no quedó tomado)
    assert ai._ai_complete_raw('s', 'p', 10) == ('x', 'g')
    assert ai._AI_SEM.acquire(timeout=0.1)
    ai._AI_SEM.release()


def test_semaforo_ia_es_reentrante_y_se_libera_tras_error(monkeypatch):
    import threading as _th
    from core import ai
    monkeypatch.setattr(ai, '_AI_SEM', _th.BoundedSemaphore(1))
    monkeypatch.setattr(ai, 'AI_BUSY_WAIT_S', 0.2)
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: _Resp(
        200, {'candidates': [{'content': {'parts': [{'text': 'dentro'}]}}]}))
    # la cascada toma el cupo y el proveedor (que también lo pide) NO se bloquea
    with ai._ai_slot():
        assert ai._complete_gemini('', 'p', 5)[0] == 'dentro'
    with pytest.raises(ValueError):
        with ai._ai_slot():
            raise ValueError('x')
    assert ai._AI_SEM.acquire(timeout=0.1)     # el error no dejó el cupo tomado
    ai._AI_SEM.release()


def test_engine_con_timeouts_de_pool_conexion_y_consulta():
    from ontology import db
    kw = db._engine_kwargs('postgresql+psycopg2://u:p@h:5432/x')
    assert kw['pool_timeout'] == db.DB_POOL_TIMEOUT_S <= 30
    assert kw['connect_args']['connect_timeout'] == db.DB_CONNECT_TIMEOUT_S
    assert f'statement_timeout={db.DB_STATEMENT_TIMEOUT_MS}' in kw['connect_args']['options']
    # con otro driver no se pasan parámetros de libpq (romperían la conexión)
    assert 'connect_args' not in db._engine_kwargs('sqlite:///x.db')


# ════════════════════════════════════════════════════════════════════════════
# #17 · #20 — guardas de las rutas (sin base: se simula "base disponible")
# ════════════════════════════════════════════════════════════════════════════

_APP = {}


def _client():
    if 'app' not in _APP:
        from flask import Flask
        from matrix.api import matrix_bp
        from ontology.api import ontology_bp
        app = Flask('infra_test')
        app.config['TESTING'] = True
        app.register_blueprint(ontology_bp)
        app.register_blueprint(matrix_bp)
        _APP['app'] = app
    return _APP['app'].test_client()


@pytest.fixture
def clean_limits():
    from core import http as h
    from core import pin
    pin._reset_for_tests()
    with h._rate_lock:
        h._rate_buckets.clear()
    yield
    pin._reset_for_tests()
    with h._rate_lock:
        h._rate_buckets.clear()


PROTECTED = [
    ('/api/ontology/actions/AnotarObjeto', {'actor': 'x', 'object_id': 'A', 'texto': 't'}),
    ('/api/ontology/events', {'event_type': 'ObjectCreated', 'valid_from': '2020-01-01', 'source': 's',
                              'actor': 'x', 'payload': {'label': 'X', 'type': 'Company'}, 'object_id': 'X'}),
    ('/api/ontology/bulk/import', {'actor': 'x', 'objects': []}),
    ('/api/ontology/agents/run', {}),
    ('/api/ontology/agents/cycle', {'force': True}),     # el latido SIN force no pide PIN (ver abajo)
    ('/api/ontology/agents/investigar', {'query': 'q', 'actor': 'x'}),
    (f'/api/ontology/agents/proposals/{uuid.uuid4()}/approve', {'actor': 'x'}),
    (f'/api/ontology/agents/proposals/{uuid.uuid4()}/reject', {'actor': 'x'}),
]


@pytest.mark.parametrize('url,body', PROTECTED)
def test_escrituras_de_ontologia_exigen_pin(monkeypatch, clean_limits, url, body):
    monkeypatch.setattr('ontology.api.ontology_available', lambda: True)
    monkeypatch.setenv('TRADE_PIN', PIN)
    c = _client()
    r = c.post(url, json=body)
    assert r.status_code == 401, (url, r.status_code, r.get_json())
    assert r.get_json()['code'] == 'invalid_pin'
    r2 = c.post(url, json=body, headers={'X-Trade-Pin': 'mal-' + PIN})
    assert r2.status_code == 401


def test_pin_incorrecto_en_ontologia_cuenta_para_el_bloqueo(monkeypatch, clean_limits):
    monkeypatch.setattr('ontology.api.ontology_available', lambda: True)
    monkeypatch.setenv('TRADE_PIN', PIN)
    from core import pin
    c = _client()
    for _ in range(pin.PIN_MAX_FAILS):
        assert c.post('/api/ontology/events', json={}, headers={'X-Trade-Pin': 'nope'}).status_code == 401
    r = c.post('/api/ontology/events', json={}, headers={'X-Trade-Pin': PIN})
    assert r.status_code == 429 and r.get_json()['code'] == 'pin_locked'


@pytest.mark.parametrize('method,url,fname', [
    ('post', '/api/ontology/ingest/news', 'ingest_news'),
    ('post', '/api/ontology/alerts', 'alerts_create'),
    ('get', '/api/ontology/alerts/check', 'alerts_check'),
    ('get', '/api/ontology/agents/brief', 'agents_brief'),
    ('post', '/api/matrix/impact', 'matrix_impact'),
    ('post', '/api/matrix/insights', 'matrix_insights'),
    ('post', '/api/matrix/simulations', 'matrix_save_sim'),
    ('post', '/api/matrix/factor/fire', 'matrix_factor_fire'),
    ('get', '/api/matrix/metrics', 'matrix_metrics'),
    ('get', '/api/matrix/supply', 'matrix_get'),
    ('get', '/api/matrix/parity', 'matrix_parity'),
    ('post', '/api/ontology/agents/cycle', 'agents_cycle'),
])
def test_rutas_abiertas_y_pesadas_tienen_limite_de_tasa(monkeypatch, clean_limits, method, url, fname):
    monkeypatch.setattr('ontology.api.ontology_available', lambda: True)
    from core import http as h
    with h._rate_lock:
        h._rate_buckets[f'127.0.0.1:{fname}'] = [time.time()] * 500
    r = getattr(_client(), method)(url, json={})
    assert r.status_code == 429, (url, r.status_code)
    d = r.get_json()
    assert d['code'] == 'rate_limited' and d['error'] and d['error_en']


def test_rate_limit_usa_el_ultimo_salto_de_xff(monkeypatch, clean_limits):
    """El primer salto de X-Forwarded-For lo escribe el cliente: rotarlo NO da cupo nuevo."""
    monkeypatch.setattr('matrix.api._db', lambda: None)       # 503 barato tras el límite
    from core import http as h
    with h._rate_lock:
        h._rate_buckets['10.0.0.9:matrix_impact'] = [time.time()] * 500
    r = _client().post('/api/matrix/impact', json={}, headers={'X-Forwarded-For': '1.2.3.4, 10.0.0.9'})
    assert r.status_code == 429


@pytest.mark.parametrize('body,key', [
    ({'shock': ['A'], 'damping': 'abc'}, 'damping'),
    ({'shock': ['A'], 'max_hops': 'nan'}, 'max_hops'),
    ({'shock': ['A'], 'n_samples': 'inf'}, 'n_samples'),
    ({'shock': ['A'], 'magnitude': [1]}, 'magnitude'),
])
def test_impact_parametro_no_numerico_da_400_bilingue(monkeypatch, clean_limits, body, key):
    monkeypatch.setattr('matrix.api._db', lambda: (lambda: None))   # "hay base" (no se llega a usar)
    r = _client().post('/api/matrix/impact', json=body)
    assert r.status_code == 400
    d = r.get_json()
    assert key in d['error'] and key in d['error_en']


def test_impact_as_of_basura_da_400(monkeypatch, clean_limits):
    monkeypatch.setattr('matrix.api._db', lambda: (lambda: None))
    r = _client().post('/api/matrix/impact', json={'shock': ['A'], 'as_of': 'ayer por la tarde'})
    assert r.status_code == 400 and r.get_json()['error_en'].startswith('invalid as_of')


def test_num_acota_rangos():
    from matrix.api import DAMPING_MAX, MAX_HOPS_CAP, N_SAMPLES_CAP, _num
    assert _num({'d': 5}, 'd', 0.6, 0.0, DAMPING_MAX) == 0.95
    assert _num({'d': -3}, 'd', 0.6, 0.0, DAMPING_MAX) == 0.0
    assert _num({'h': 10 ** 9}, 'h', 6, 1, MAX_HOPS_CAP, int) == 12
    assert _num({'n': 10 ** 9}, 'n', 1, 1, N_SAMPLES_CAP, int) == 100
    assert _num({}, 'n', 1, 1, N_SAMPLES_CAP, int) == 1


# ════════════════════════════════════════════════════════════════════════════
# Con Postgres: #2 statement_timeout, #17 clamps reales, #20 PIN correcto,
# #22 aprobación atómica
# ════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema()
    with session_scope() as s:
        for oid in ('INF_A', 'INF_B', 'INF_C'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company', 'properties': {}},
                        valid_from='2000-01-01', source='test', actor='pytest', object_id=oid)
        for a, b in (('INF_A', 'INF_B'), ('INF_B', 'INF_C')):
            apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 1.0, 'properties': {}},
                        valid_from='2000-01-01', source='test', actor='pytest', object_id=a, target_id=b)
        apply_event(s, 'ObjectCreated', {'label': 'Factor test', 'type': 'Factor',
                                         'properties': {'severity': 1.0, 'severity_crisis': 8.0}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='INF_FX')
        apply_event(s, 'LinkCreated', {'rel_type': 'affects', 'weight': 0.5, 'properties': {}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='INF_FX', target_id='INF_A')
    yield
    Base.metadata.drop_all(engine)


@needs_db
def test_statement_timeout_activo_en_la_sesion(db):
    from sqlalchemy import text
    from ontology.db import DB_STATEMENT_TIMEOUT_MS, session_scope
    with session_scope() as s:
        v = s.execute(text('SHOW statement_timeout')).scalar()
    assert v in (f'{DB_STATEMENT_TIMEOUT_MS // 1000}s', f'{DB_STATEMENT_TIMEOUT_MS}ms')


@needs_db
def test_impact_acota_hops_damping_y_muestras(db, monkeypatch, clean_limits):
    import matrix.engine as E
    seen = {}
    real_prop, real_bands = E.propagate, E.propagate_bands

    def spy_prop(*a, **k):
        seen.setdefault('prop', k)
        return real_prop(*a, **k)

    def spy_bands(*a, **k):
        seen['bands'] = k
        k2 = dict(k)
        k2['n_samples'] = 3                    # rápido: lo que importa es lo que llegó
        return real_bands(*a, **k2)

    monkeypatch.setattr(E, 'propagate', spy_prop)
    monkeypatch.setattr(E, 'propagate_bands', spy_bands)
    r = _client().post('/api/matrix/impact', json={
        'shock': ['INF_A'], 'max_hops': 10 ** 6, 'damping': 7, 'n_samples': 10 ** 6, 'magnitude': 99,
        'rel_weights': {'supply': 'x', 'fab': 50, 'inventado': 3}})
    assert r.status_code == 200, r.get_json()
    k = seen['prop']
    assert k['max_hops'] == 12 and k['damping'] == 0.95 and k['magnitude'] == 5.0
    assert k['rel_weights'] == {'fab': 2.0}
    assert seen['bands']['n_samples'] == 100          # ~5 s de CPU (500 eran ~26-46 s)
    assert r.get_json()['impacts']['INF_A'] == 100.0


@needs_db
def test_factor_fire_acota_parametros(db, monkeypatch, clean_limits):
    import matrix.engine as E
    seen = {}
    real = E.propagate

    def spy(*a, **k):
        seen.update(k)
        return real(*a, **k)

    monkeypatch.setattr(E, 'propagate', spy)
    r = _client().post('/api/matrix/factor/fire', json={'factor_id': 'INF_FX', 'damping': 3, 'max_hops': 400})
    assert r.status_code == 200, r.get_json()
    assert seen['damping'] == 0.95 and seen['max_hops'] == 12
    assert seen['magnitude'] == pytest.approx(8.0 / 5.0)
    bad = _client().post('/api/matrix/factor/fire', json={'factor_id': 'INF_FX', 'damping': 'x'})
    assert bad.status_code == 400


@needs_db
def test_accion_con_pin_correcto_o_sin_trade_pin_pasa(db, monkeypatch, clean_limits):
    c = _client()
    body = {'actor': 'ana', 'object_id': 'INF_A', 'texto': 'nota'}
    monkeypatch.delenv('TRADE_PIN', raising=False)       # desarrollo: sin PIN configurado se permite
    assert c.post('/api/ontology/actions/AnotarObjeto', json=body).status_code == 200
    monkeypatch.setenv('TRADE_PIN', PIN)
    assert c.post('/api/ontology/actions/AnotarObjeto', json=body).status_code == 401
    r = c.post('/api/ontology/actions/AnotarObjeto', json=body, headers={'X-Trade-Pin': PIN})
    assert r.status_code == 200, r.get_json()


def _new_proposal(payload=None, action_type='AnotarObjeto'):
    from ontology.db import session_scope
    from ontology.models import ProposedAction
    with session_scope() as s:
        p = ProposedAction(agent='agente_test', action_type=action_type,
                           payload=payload or {'object_id': 'INF_A', 'texto': 'propuesta'},
                           object_id='INF_A', confidence=0.9, explanation='test', status='pending')
        s.add(p)
        s.flush()
        return str(p.id)


def _status(pid):
    from ontology.db import session_scope
    from ontology.models import ProposedAction
    with session_scope() as s:
        return s.get(ProposedAction, uuid.UUID(pid)).status


@needs_db
def test_aprobar_dos_veces_a_la_vez_ejecuta_una_sola(db, monkeypatch, clean_limits):
    """#22: dos aprobaciones SIMULTÁNEAS (dos clics / dos pestañas): exactamente
    una ejecuta la Acción; la otra recibe 409."""
    monkeypatch.delenv('TRADE_PIN', raising=False)
    import ontology.actions as A
    real = A.execute_action
    calls = []

    def slow_exec(*a, **k):
        calls.append(1)
        time.sleep(0.6)            # la 1ª transacción sigue abierta mientras llega la 2ª
        return real(*a, **k)

    monkeypatch.setattr(A, 'execute_action', slow_exec)
    pid = _new_proposal()
    barrier = threading.Barrier(2)
    results = []

    def approve():
        c = _client()
        barrier.wait(5)
        r = c.post(f'/api/ontology/agents/proposals/{pid}/approve', json={'actor': 'ana'})
        results.append(r.status_code)

    ts = [threading.Thread(target=approve) for _ in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(20)
    assert sorted(results) == [200, 409], results
    assert len(calls) == 1
    assert _status(pid) == 'approved'
    # y un tercer intento (o un rechazo tardío) tampoco la toca
    c = _client()
    assert c.post(f'/api/ontology/agents/proposals/{pid}/approve', json={'actor': 'ana'}).status_code == 409
    r = c.post(f'/api/ontology/agents/proposals/{pid}/reject', json={'actor': 'ana'})
    assert r.status_code == 409 and r.get_json()['code'] == 'already_resolved'


@needs_db
def test_si_la_accion_falla_la_propuesta_sigue_pendiente(db, monkeypatch, clean_limits):
    monkeypatch.delenv('TRADE_PIN', raising=False)
    pid = _new_proposal(payload={'object_id': 'NO_EXISTE_123', 'texto': 'x'})
    c = _client()
    r = c.post(f'/api/ontology/agents/proposals/{pid}/approve', json={'actor': 'ana'})
    assert r.status_code == 400
    assert _status(pid) == 'pending'       # el rollback deshizo el reclamo
    assert c.post(f'/api/ontology/agents/proposals/{pid}/reject', json={'actor': 'ana'}).status_code == 200
    assert _status(pid) == 'rejected'


@needs_db
def test_propuesta_inexistente_404_y_edits_invalidos_400(db, monkeypatch, clean_limits):
    monkeypatch.delenv('TRADE_PIN', raising=False)
    c = _client()
    assert c.post(f'/api/ontology/agents/proposals/{uuid.uuid4()}/approve',
                  json={'actor': 'ana'}).status_code == 404
    pid = _new_proposal()
    assert c.post(f'/api/ontology/agents/proposals/{pid}/approve',
                  json={'actor': 'ana', 'edits': ['no', 'dict']}).status_code == 400
    assert _status(pid) == 'pending'


# ════════════════════════════════════════════════════════════════════════════
# #6 — REMIGRATE_ON_BOOT: base desechable, el libro de clientes sobrevive
# ════════════════════════════════════════════════════════════════════════════

TINY_GRAPH = {
    'nodes': [{'id': 'RM_A', 'label': 'RM A'}, {'id': 'RM_B', 'label': 'RM B'}],
    'links': [{'source': 'RM_A', 'target': 'RM_B', 'type': 'supply', 'w': 1, 'rel': 'x'}],
    'ontology': {'objects': []},
    'temporal_facts': [],
}


@pytest.fixture
def throwaway_db(tmp_path):
    """Una base NUEVA solo para este test (se borra al final) y ontology.db
    apuntando a ella; al terminar se restaura la base de la suite."""
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    import json

    import psycopg2
    from sqlalchemy.engine import make_url

    import ontology.db as odb
    base = make_url(DATABASE_URL)
    name = f'{base.database}_remig_{uuid.uuid4().hex[:8]}'
    admin = psycopg2.connect(host=base.host, port=base.port or 5432, user=base.username,
                             password=base.password, dbname='postgres')
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(f'CREATE DATABASE "{name}"')
    url = base.set(database=name).render_as_string(hide_password=False)
    saved = (odb.DATABASE_URL, odb._engine, odb._SessionLocal)
    odb.DATABASE_URL, odb._engine, odb._SessionLocal = url, None, None
    graph = tmp_path / 'grafo_tiny.json'
    graph.write_text(json.dumps(TINY_GRAPH), encoding='utf-8')
    try:
        odb.init_schema()
        yield {'name': name, 'url': url, 'graph': str(graph)}
    finally:
        if odb._engine is not None:
            odb._engine.dispose()
        odb.DATABASE_URL, odb._engine, odb._SessionLocal = saved
        with admin.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        admin.close()


def _seed_obj(oid):
    from ontology.db import session_scope
    from ontology.service import apply_event
    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company', 'properties': {}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id=oid)


def _has_obj(oid):
    from ontology.db import session_scope
    from ontology.models import ObjectRecord
    with session_scope() as s:
        return s.get(ObjectRecord, oid) is not None


def _count(model):
    from ontology.db import session_scope
    with session_scope() as s:
        return s.query(model).count()


@needs_db
@pytest.mark.parametrize('flag', ['1', 'true', 'yes', 'railway', ''])
def test_remigrate_se_niega_si_el_valor_no_es_el_nombre_de_la_base(throwaway_db, monkeypatch, flag):
    from scripts.migrate_v0_to_ontology import RemigrateRefused, run_migration
    _seed_obj('KEEP_ME')
    monkeypatch.setenv('REMIGRATE_ON_BOOT', flag)
    logs = []
    with pytest.raises(RemigrateRefused) as ei:
        run_migration(reset=True, graph_path=throwaway_db['graph'], log=logs.append)
    assert throwaway_db['name'] in str(ei.value)          # dice qué valor poner
    assert 'Nothing was deleted' in str(ei.value)
    assert any('NEGADA' in m for m in logs)
    assert _has_obj('KEEP_ME')


@needs_db
def test_remigrate_se_niega_con_clientes_de_corretaje(throwaway_db, monkeypatch):
    from brokerage.models import BrokerClient
    from ontology.db import session_scope
    from scripts.migrate_v0_to_ontology import RemigrateRefused, run_migration
    _seed_obj('KEEP_ME')
    with session_scope() as s:
        s.add(BrokerClient(name='Cliente Real'))
    monkeypatch.setenv('REMIGRATE_ON_BOOT', throwaway_db['name'])
    with pytest.raises(RemigrateRefused) as ei:
        run_migration(reset=True, graph_path=throwaway_db['graph'], log=lambda m: None)
    assert 'broker_clients' in str(ei.value)
    assert _count(BrokerClient) == 1
    assert _has_obj('KEEP_ME')


@needs_db
def test_remigrate_con_nombre_correcto_borra_solo_el_grafo(throwaway_db, monkeypatch):
    from sqlalchemy import inspect

    from brokerage.models import BrokerAudit
    from mcp_server.models import McpAudit
    from ontology.db import _get_engine, session_scope
    from ontology.models import Alert, ProposedAction
    from research.models import ResearchJob
    from scripts.migrate_v0_to_ontology import run_migration
    _seed_obj('OBJETO_VIEJO')
    with session_scope() as s:
        s.add(Alert(owner='ana', rule={'entity': 'RM_A', 'metric': 'price', 'op': '>', 'value': 1}))
        s.add(ProposedAction(agent='a', action_type='AnotarObjeto', payload={}, status='pending'))
        s.add(McpAudit(status='ok', method='tools/call'))
        s.add(ResearchJob(entity_id='RM_A', depth='QUICK'))
    # broker_audit con filas NO bloquea (solo el libro de clientes/órdenes lo hace)… salvo
    # que sea broker_*: la regla es "cualquier broker_* con filas" → aquí vacías.
    monkeypatch.setenv('REMIGRATE_ON_BOOT', throwaway_db['name'])
    logs = []
    assert run_migration(reset=True, graph_path=throwaway_db['graph'], log=logs.append) is True
    assert any('SOLO links, events, objects' in m for m in logs), logs
    assert not _has_obj('OBJETO_VIEJO')
    assert _has_obj('RM_A') and _has_obj('RM_B')
    # todo lo que NO es el grafo sobrevive
    assert _count(Alert) == 1 and _count(ProposedAction) == 1
    assert _count(McpAudit) == 1 and _count(ResearchJob) == 1
    tablas = set(inspect(_get_engine()).get_table_names())
    for t in ('broker_clients', 'broker_orders', 'broker_audit', 'broker_oauth_states',
              'mcp_tokens', 'research_claims', 'alerts', 'proposed_actions', 'insight_snapshots'):
        assert t in tablas, f'{t} desapareció'
    assert _count(BrokerAudit) == 0


def _cli(url, *args, extra_env=None):
    env = {k: v for k, v in os.environ.items()
           if k not in ('REMIGRATE_ON_BOOT', 'RAILWAY_ENVIRONMENT', 'RAILWAY_ENVIRONMENT_NAME', 'RAILWAY_PROJECT_ID')}
    env.update({'DATABASE_URL': url, 'PYTHONIOENCODING': 'utf-8'}, **(extra_env or {}))
    script = os.path.join(ROOT, 'scripts', 'migrate_v0_to_ontology.py')
    return subprocess.run([sys.executable, script, *args], capture_output=True, text=True, env=env, timeout=240)


@needs_db
def test_cli_reset_en_produccion_exige_confirm_db(throwaway_db):
    _seed_obj('KEEP_ME')
    r = _cli(throwaway_db['url'], '--reset', '--graph', throwaway_db['graph'],
             extra_env={'RAILWAY_ENVIRONMENT': 'production'})
    assert r.returncode == 2, r.stdout + r.stderr
    assert 'NEGADA' in r.stderr
    assert _has_obj('KEEP_ME')
    r2 = _cli(throwaway_db['url'], '--reset', '--confirm-db', throwaway_db['name'], '--graph', throwaway_db['graph'],
              extra_env={'RAILWAY_ENVIRONMENT': 'production'})
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert not _has_obj('KEEP_ME') and _has_obj('RM_A')


# ════════════════════════════════════════════════════════════════════════════
# Revisión 2026-09-30 — hallazgos del revisor sobre el trabajo del grupo INFRA
# ════════════════════════════════════════════════════════════════════════════

# ── (9) IA: cupo reservado al usuario, pings sin cupo, reintento solo en 429/5xx ──

def test_trabajo_de_fondo_no_ocupa_el_cupo_reservado_al_usuario(monkeypatch):
    """Con 2 cupos y 1 reservado, un hilo de FONDO (sin petición HTTP) que ya
    ocupa su único cupo de fondo no deja entrar a otro hilo de fondo, pero una
    petición interactiva SÍ entra (Khipu no responde 'IA ocupada' por culpa de
    una tanda de investigaciones automáticas)."""
    import threading as _th

    from flask import Flask

    from core import ai
    monkeypatch.setattr(ai, '_AI_SEM', _th.BoundedSemaphore(2))
    monkeypatch.setattr(ai, '_AI_BG_SEM', _th.BoundedSemaphore(1))
    monkeypatch.setattr(ai, 'AI_BUSY_WAIT_S', 0.3)
    holding, release = _th.Event(), _th.Event()

    def hog():                                  # hilo sin contexto de petición = fondo
        with ai._ai_slot():
            holding.set()
            release.wait(5)

    t = _th.Thread(target=hog)
    t.start()
    try:
        assert holding.wait(5)
        # otro trabajo de fondo: rechazado rápido
        with pytest.raises(ai.AIBusyError):
            with ai._ai_slot():
                pass
        # ai_background(False) / una petición HTTP: pasa por el cupo reservado
        with ai.ai_background(False):
            with ai._ai_slot():
                pass
        app = Flask('ai_reserve')
        with app.test_request_context('/api/x'):
            assert ai._is_background() is False
            with ai._ai_slot():
                pass
        assert ai._is_background() is True
    finally:
        release.set()
        t.join(5)
    # todos los cupos quedaron libres
    assert ai._AI_SEM.acquire(timeout=0.1) and ai._AI_SEM.acquire(timeout=0.1)
    ai._AI_SEM.release()
    ai._AI_SEM.release()
    assert ai._AI_BG_SEM.acquire(timeout=0.1)
    ai._AI_BG_SEM.release()


def test_ping_del_diagnostico_no_espera_cupo(monkeypatch):
    """El 🩺 llama a _complete_gemini('', 'ping', 1): con la IA saturada no debe
    informar 'IA ocupada' como si Gemini estuviera caído."""
    import threading as _th

    from core import ai
    monkeypatch.setattr(ai, '_AI_SEM', _th.BoundedSemaphore(1))
    monkeypatch.setattr(ai, 'AI_BUSY_WAIT_S', 0.2)
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: _Resp(
        200, {'candidates': [{'content': {'parts': [{'text': 'pong'}]}}]}))
    assert ai._AI_SEM.acquire(timeout=1)       # IA saturada
    try:
        assert ai._complete_gemini('', 'ping', 1)[0] == 'pong'
        with pytest.raises(ai.AIBusyError):     # una llamada normal sí espera cupo
            ai._complete_gemini('', 'hola', 200)
    finally:
        ai._AI_SEM.release()


def _fake_anthropic(monkeypatch, plan):
    """Cliente Anthropic falso: `plan` = lista de excepciones/textos por llamada."""
    import anthropic

    from core import ai
    calls = []

    class FakeClient:
        def __init__(self, **kw):
            self.kw = kw
            self.messages = self

        def create(self, **kw):
            calls.append(kw['model'])
            step = plan[min(len(calls) - 1, len(plan) - 1)]
            if isinstance(step, BaseException):
                raise step
            return _FakeMsg(step)

    monkeypatch.setattr(ai, 'CLAUDE', 'sk-test-123456')
    monkeypatch.setattr(ai, 'CLAUDE_RETRY_SLEEP_S', 0)
    monkeypatch.setattr(anthropic, 'Anthropic', FakeClient)
    return calls


def _httpx():
    # el SDK de anthropic 1.x usa el paquete httpx2 (antes httpx)
    try:
        import httpx2 as hx
    except ImportError:  # pragma: no cover
        import httpx as hx
    return hx


def _status_error(code):
    import anthropic
    httpx = _httpx()
    req = httpx.Request('POST', 'https://api.anthropic.test/v1/messages')
    resp = httpx.Response(code, request=req, json={'error': {'type': 'overloaded_error', 'message': 'x'}})
    return anthropic.APIStatusError('overloaded', response=resp, body=None)


def test_claude_reintenta_una_vez_la_sobrecarga_529(monkeypatch):
    from core import ai
    calls = _fake_anthropic(monkeypatch, [_status_error(529), 'ok tras reintento'])
    assert ai._complete_claude('s', 'p', 10, model='claude-a')[0] == 'ok tras reintento'
    assert calls == ['claude-a', 'claude-a']          # mismo modelo, UN reintento


def test_claude_no_reintenta_un_400(monkeypatch):
    from core import ai
    calls = _fake_anthropic(monkeypatch, [_status_error(400)])
    monkeypatch.setattr(ai, 'AI_MODEL_FAST', 'claude-a')
    with pytest.raises(RuntimeError):
        ai._complete_claude('s', 'p', 10, model='claude-a')
    assert calls.count('claude-a') == 1


def test_claude_timeout_real_del_sdk_no_se_reintenta(monkeypatch):
    import anthropic

    from core import ai
    httpx = _httpx()
    to = anthropic.APITimeoutError(request=httpx.Request('POST', 'https://api.anthropic.test/v1/messages'))
    calls = _fake_anthropic(monkeypatch, [to])
    with pytest.raises(RuntimeError) as ei:
        ai._complete_claude('s', 'p', 10, model='claude-a')
    assert calls == ['claude-a'] and 'Timeout' in str(ei.value)


# ── (7) pool de la base acorde a 12 hilos + fondo ──

def test_pool_de_la_base_cubre_los_hilos(monkeypatch):
    from ontology import db
    kw = db._engine_kwargs('postgresql+psycopg2://u:p@h:5432/x')
    assert kw['pool_size'] + kw['max_overflow'] >= 16      # 12 hilos de gunicorn + fondo
    assert kw['pool_size'] == db.DB_POOL_SIZE and kw['max_overflow'] == db.DB_MAX_OVERFLOW
    monkeypatch.setenv('DB_POOL_SIZE', '999')
    assert db._env_int('DB_POOL_SIZE', 10, 1, 50) == 50     # acotado: Railway admite 100 conexiones
    monkeypatch.setenv('DB_POOL_SIZE', 'abc')
    assert db._env_int('DB_POOL_SIZE', 10, 1, 50) == 10


# ── (3)/(4) ciclo del Radar: latido sin PIN, force con PIN, una sola corrida ──

def test_latido_del_radar_sin_pin_no_da_401(monkeypatch, clean_limits):
    """engine/live.js manda POST /agents/cycle sin PIN cada 10 min: con TRADE_PIN
    puesto en producción recibía 401 y el Radar se apagaba en silencio."""
    import ontology.api as oapi
    monkeypatch.setattr('ontology.api.ontology_available', lambda: True)
    monkeypatch.setenv('TRADE_PIN', PIN)
    started = []
    monkeypatch.setattr(oapi, '_try_start_cycle', lambda force: started.append(force) or True)
    c = _client()
    r = c.post('/api/ontology/agents/cycle', json={'actor': 'live'})
    assert r.status_code == 200 and r.get_json()['started_new_run'] is True
    assert started == [False]
    # forzar sin PIN → 401; con PIN errado → 401 y cuenta; con PIN → 200
    assert c.post('/api/ontology/agents/cycle', json={'force': True}).status_code == 401
    r = c.post('/api/ontology/agents/cycle', json={}, headers={'X-Trade-Pin': 'mal'})
    assert r.status_code == 401
    from core import pin
    assert len(pin._FAILS.get('127.0.0.1', [])) == 1
    r = c.post('/api/ontology/agents/cycle', json={'force': True}, headers={'X-Trade-Pin': PIN})
    assert r.status_code == 200 and started == [False, True]


def test_ciclo_simultaneo_arranca_una_sola_corrida(monkeypatch):
    import ontology.api as oapi
    monkeypatch.setitem(oapi._cycle_state, 'running', False)
    monkeypatch.setitem(oapi._cycle_state, 'last_at', 0.0)
    gate = threading.Event()
    runs = []

    def slow_bg():
        runs.append(1)
        gate.wait(5)
        with oapi._cycle_lock:
            oapi._cycle_state['running'] = False
            oapi._cycle_state['last_at'] = time.time()

    monkeypatch.setattr(oapi, '_cycle_bg', slow_bg)
    barrier = threading.Barrier(8)
    results = []

    def go():
        barrier.wait(5)
        results.append(oapi._try_start_cycle(False))

    ts = [threading.Thread(target=go) for _ in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(5)
    gate.set()
    for _ in range(50):
        if not oapi._cycle_state['running']:
            break
        time.sleep(0.05)
    assert results.count(True) == 1 and len(runs) == 1
    # recién terminada: sin force no arranca otra antes de 5 min
    assert oapi._try_start_cycle(False) is False


# ── (11) cuerpos que no son objeto y parámetros de URL inválidos → 400, no 500 ──

@pytest.mark.parametrize('verb', ['approve', 'reject'])
def test_cuerpo_json_lista_da_400_no_500(monkeypatch, clean_limits, verb):
    monkeypatch.setattr('ontology.api.ontology_available', lambda: True)
    monkeypatch.delenv('TRADE_PIN', raising=False)
    r = _client().post(f'/api/ontology/agents/proposals/{uuid.uuid4()}/{verb}', json=['x', 'y'])
    assert r.status_code == 400 and r.get_json()['error_en'] == 'actor is required'


@pytest.mark.parametrize('url', ['/api/ontology/objects?limit=abc',
                                 '/api/ontology/agents/proposals?limit=1e9x',
                                 '/api/ontology/agents/brief?hours=mucho',
                                 '/api/ontology/actions?limit=%20x'])
def test_parametro_entero_invalido_da_400_bilingue(monkeypatch, clean_limits, url):
    monkeypatch.setattr('ontology.api.ontology_available', lambda: True)
    r = _client().get(url)
    assert r.status_code == 400, (url, r.status_code)
    d = r.get_json()
    assert d['error'] and d['error_en']


# ── (2)/(6) motor de matrices: as_of normalizado, límites de cálculo pesado ──

@pytest.mark.parametrize('raw,want', [
    ('2024-01-03', '2024-01-03'),
    ('2024-01-03T00:00:00Z', '2024-01-03'),
    ('2024-01-03T00:00:00', '2024-01-03'),                 # sin zona → UTC (antes 500)
    ('2024-01-02T21:00:00-03:00', '2024-01-03'),           # misma medianoche UTC
    ('2024-01-03T10:30:00', '2024-01-03T10:30:00+00:00'),
    (None, None), ('', None),
])
def test_as_of_se_normaliza_a_utc(raw, want):
    from matrix.api import _as_of_norm
    with _client().application.app_context():
        got, err = _as_of_norm(raw)
    assert err is None and got == want


@pytest.mark.parametrize('raw', ['ayer', '2024-13-45', 12345, ['2024-01-01'], '9' * 60])
def test_as_of_invalido_da_400(raw):
    from matrix.api import _as_of_norm
    with _client().application.app_context():
        got, err = _as_of_norm(raw)
    assert got is None and err[1] == 400


def test_matrix_query_invalida_da_400(monkeypatch, clean_limits):
    monkeypatch.setattr('matrix.api._db', lambda: (lambda: None))   # "hay base" (no se llega a usar)
    c = _client()
    assert c.get('/api/matrix/factors?as_of=basura').status_code == 400
    assert c.get('/api/matrix/simulations?limit=abc').status_code == 400
    assert c.get('/api/matrix/metrics?as_of=basura').status_code == 400
    assert c.get('/api/matrix/supply?as_of=basura').status_code == 400


def test_ttl_cache_descarta_lo_mas_viejo_no_todo(monkeypatch):
    import matrix.api as M
    monkeypatch.setattr(M, '_TTL_CACHE', {})
    monkeypatch.setattr(M, '_TTL_MAX', 5)
    M._ttl_set('metrics:now', 'CARO')
    for i in range(10):
        time.sleep(0.001)
        M._ttl_set(f'k{i}', i)
    assert len(M._TTL_CACHE) == 5
    assert 'k9' in M._TTL_CACHE


# ── (5)/(10) re-migración: CLI solo local sin --confirm-db; arranque una sola vez ──

@pytest.mark.parametrize('url,ok', [
    ('postgresql://postgres:x@localhost:5432/khipus_test', True),
    ('postgresql://postgres:x@127.0.0.1/khipus_test', True),
    ('postgresql://postgres:x@[::1]:5432/dev', True),
    ('postgresql:///dev', True),
    ('postgresql://u@/dev?host=/var/run/postgresql', True),
    ('postgres://postgres:x@localhost/dev', True),
    ('postgresql://postgres:x@monorail.proxy.rlwy.net:41234/railway', False),
    ('postgresql://postgres:x@db.example.com:5432/dev', False),
    ('postgresql://postgres:x@localhost:5432/railway', False),      # base de producción copiada
    ('postgresql://u@/dev?host=db.example.com', False),
    ('', False), ('no-es-una-url', False),
])
def test_reset_sin_confirmacion_solo_en_base_local(url, ok):
    from scripts.migrate_v0_to_ontology import _local_reset_ok
    assert _local_reset_ok(url) is ok


def test_cli_reset_contra_host_remoto_se_niega_sin_conectar():
    """La URL pública de Railway copiada a una terminal local: --reset sin
    --confirm-db se niega ANTES de conectar (host inexistente → no hay espera)."""
    t0 = time.time()
    r = _cli('postgresql://postgres:x@khipu-remoto.invalid:5432/railway', '--reset')
    assert r.returncode == 2, r.stdout + r.stderr
    assert 'NEGADA' in r.stderr and 'REFUSED' in r.stderr and '--confirm-db' in r.stderr
    assert time.time() - t0 < 60


@needs_db
def test_remigrate_del_arranque_corre_una_sola_vez(throwaway_db, monkeypatch):
    """REMIGRATE_ON_BOOT=<base> olvidada en Railway + restartPolicy ALWAYS: los
    reinicios siguientes NO vuelven a borrar el grafo; '<base>:2' sí re-migra."""
    from scripts.migrate_v0_to_ontology import (RemigrateRefused, remigrate_flag_warning,
                                                run_migration)
    name = throwaway_db['name']
    monkeypatch.setenv('REMIGRATE_ON_BOOT', name)
    assert run_migration(reset=True, graph_path=throwaway_db['graph'], log=lambda m: None) is True
    _seed_obj('TESIS_NUEVA')                      # algo creado DESPUÉS de re-migrar
    logs = []
    with pytest.raises(RemigrateRefused) as ei:   # reinicio con la variable aún puesta
        run_migration(reset=True, graph_path=throwaway_db['graph'], log=logs.append)
    msg = str(ei.value)
    assert 'YA se ejecutó' in msg and 'already ran' in msg and f'{name}:2' in msg
    assert _has_obj('TESIS_NUEVA')
    w = remigrate_flag_warning()
    assert w['code'] == 'remigrate_flag_set' and w['already_ran_at'] and w['warning_en']
    # re-migrar otra vez A PROPÓSITO: etiqueta nueva
    monkeypatch.setenv('REMIGRATE_ON_BOOT', f'{name}:2')
    assert run_migration(reset=True, graph_path=throwaway_db['graph'], log=lambda m: None) is True
    assert not _has_obj('TESIS_NUEVA') and _has_obj('RM_A')
    # la etiqueta no sirve para saltarse el nombre de la base
    monkeypatch.setenv('REMIGRATE_ON_BOOT', 'otra_base:3')
    with pytest.raises(RemigrateRefused):
        run_migration(reset=True, graph_path=throwaway_db['graph'], log=lambda m: None)
    monkeypatch.delenv('REMIGRATE_ON_BOOT')
    assert remigrate_flag_warning() is None


@needs_db
def test_remigrate_en_curso_bloquea_y_uno_colgado_se_reintenta(throwaway_db, monkeypatch):
    from sqlalchemy import text

    from ontology.db import _get_engine
    from scripts.migrate_v0_to_ontology import (REMIGRATE_LOG_TABLE, RemigrateRefused,
                                                claim_boot_remigration, run_migration)
    name = throwaway_db['name']
    eng = _get_engine()
    rid = claim_boot_remigration(eng, name, name)          # "otro arranque" empezó ahora
    _seed_obj('KEEP_ME')
    monkeypatch.setenv('REMIGRATE_ON_BOOT', name)
    with pytest.raises(RemigrateRefused) as ei:
        run_migration(reset=True, graph_path=throwaway_db['graph'], log=lambda m: None)
    assert 'in progress' in str(ei.value)
    assert _has_obj('KEEP_ME')
    # ese arranque murió hace 20 min sin terminar (SIGKILL): se permite reintentar
    with eng.begin() as c:
        c.execute(text(f"UPDATE {REMIGRATE_LOG_TABLE} SET started_at = now() - interval '20 minutes' "
                       f"WHERE id = :i"), {'i': rid})
    assert run_migration(reset=True, graph_path=throwaway_db['graph'], log=lambda m: None) is True
    assert not _has_obj('KEEP_ME')


@needs_db
def test_remigrate_fallida_no_queda_registrada_como_hecha(throwaway_db, monkeypatch):
    import scripts.migrate_v0_to_ontology as mig
    name = throwaway_db['name']
    monkeypatch.setenv('REMIGRATE_ON_BOOT', name)

    def boom(*a, **k):
        raise RuntimeError('falla a mitad')

    monkeypatch.setattr(mig, '_migrate_graph', boom)
    with pytest.raises(RuntimeError):
        mig.run_migration(reset=True, graph_path=throwaway_db['graph'], log=lambda m: None)
    monkeypatch.undo()
    monkeypatch.setenv('REMIGRATE_ON_BOOT', name)
    assert mig.run_migration(reset=True, graph_path=throwaway_db['graph'], log=lambda m: None) is True


@needs_db
def test_cli_reset_local_en_base_llamada_railway_exige_confirm_db(throwaway_db, monkeypatch):
    """Defensa en profundidad: aunque la URL parezca local, si current_database()
    es 'railway' el atajo de la CLI no vale."""
    import scripts.migrate_v0_to_ontology as mig
    monkeypatch.setattr(mig, '_current_database', lambda engine: 'railway')
    _seed_obj('KEEP_ME')
    with pytest.raises(mig.RemigrateRefused):
        mig.run_migration(reset=True, graph_path=throwaway_db['graph'], log=lambda m: None,
                          confirm_db=mig._CLI_EXPLICIT)
    assert _has_obj('KEEP_ME')


# ── Con Postgres: #17 residual (métricas/bandas/insights) y #22 residual ──

@needs_db
def test_impact_as_of_sin_zona_horaria_ya_no_da_500(db, clean_limits):
    c = _client()
    r = c.post('/api/matrix/impact', json={'shock': ['INF_A'], 'as_of': '2024-01-03T00:00:00'})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()['as_of'] == '2024-01-03'
    r = c.get('/api/matrix/metrics?as_of=2024-01-03T10:00:00')
    assert r.status_code == 200, r.get_json()
    assert c.get('/api/matrix/factors?as_of=2024-01-03T00:00:00').status_code == 200


@needs_db
def test_metrics_presupuesto_y_ocupado_sirven_la_ultima_lectura(db, monkeypatch, clean_limits):
    import matrix.api as M
    import matrix.engine as E
    monkeypatch.setattr(M, '_TTL_CACHE', {})
    monkeypatch.setattr(M, '_LAST_METRICS', {})
    calls = []
    real = E.compute_metrics
    monkeypatch.setattr(E, 'compute_metrics', lambda s, as_of=None: calls.append(as_of) or real(s, as_of=as_of))
    c = _client()
    r = c.get('/api/matrix/metrics')
    assert r.status_code == 200 and 'stale' not in r.get_json()
    for _ in range(5):                               # lo cacheado no gasta presupuesto
        assert c.get('/api/matrix/metrics').status_code == 200
    assert len(calls) == 1
    # época nueva + presupuesto agotado → última lectura marcada stale (no 50 s de CPU)
    monkeypatch.setattr(M, '_TTL_CACHE', {})
    from core import http as h
    with h._rate_lock:
        h._rate_buckets['127.0.0.1:matrix_metrics_compute'] = [time.time()] * 50
    r = c.get('/api/matrix/metrics')
    assert r.status_code == 200 and r.get_json()['stale'] is True and len(calls) == 1
    # histórico sin lectura previa + presupuesto agotado → 429 bilingüe
    r = c.get('/api/matrix/metrics?as_of=2024-01-05')
    assert r.status_code == 429 and r.get_json()['code'] == 'compute_budget' and r.get_json()['error_en']
    # motor ocupado → stale (ahora) o 503 matrix_busy (histórico), rápido
    with h._rate_lock:
        h._rate_buckets.clear()
    monkeypatch.setattr(M, 'MATRIX_BUSY_WAIT_S', 0.1)
    assert M._HEAVY_SEM.acquire(timeout=1)
    try:
        r = c.get('/api/matrix/metrics')
        assert r.status_code == 200 and r.get_json()['stale'] is True
        r = c.get('/api/matrix/metrics?as_of=2024-01-06')
        assert r.status_code == 503 and r.get_json()['code'] == 'matrix_busy'
        assert r.headers.get('Retry-After') == '30'
    finally:
        M._HEAVY_SEM.release()
    assert len(calls) == 1


@needs_db
def test_bandas_omitidas_con_explicacion_si_no_hay_cupo(db, monkeypatch, clean_limits):
    import matrix.api as M
    c = _client()
    monkeypatch.setattr(M, 'MATRIX_BUSY_WAIT_S', 0.1)
    assert M._HEAVY_SEM.acquire(timeout=1)
    try:
        r = c.post('/api/matrix/impact', json={'shock': ['INF_A'], 'n_samples': 5})
    finally:
        M._HEAVY_SEM.release()
    d = r.get_json()
    assert r.status_code == 200 and 'bands' not in d and d['impacts']['INF_A'] == 100.0
    assert d['bands_skipped']['reason'] == 'busy' and d['bands_skipped']['error_en']
    from core import http as h
    with h._rate_lock:
        h._rate_buckets['127.0.0.1:matrix_bands_compute'] = [time.time()] * 50
    d = c.post('/api/matrix/impact', json={'shock': ['INF_A'], 'n_samples': 5}).get_json()
    assert d['bands_skipped']['reason'] == 'budget'
    with h._rate_lock:
        h._rate_buckets.clear()
    d = c.post('/api/matrix/impact', json={'shock': ['INF_A'], 'n_samples': 5}).get_json()
    assert 'bands' in d and d['n_samples'] == 5


@needs_db
def test_parity_tol_invalido_da_400(db, clean_limits):
    c = _client()
    assert c.get('/api/matrix/parity?tol=abc').status_code == 400
    assert c.get('/api/matrix/parity?tol=-1').status_code == 400


@needs_db
def test_insights_deep_exige_pin_y_as_of_no_ensucia_historial(db, monkeypatch, clean_limits):
    import matrix.api as M
    from ontology.db import session_scope
    from ontology.models import InsightSnapshot
    monkeypatch.setattr(M, '_TTL_CACHE', {})
    tiers = []

    def fake_narrate(situation, lang, tier):
        tiers.append(tier)
        return [{'title': 't', 'detail': 'd', 'kind': 'estructura'}], 'fake:' + tier

    monkeypatch.setattr(M, '_narrate_insights', fake_narrate)
    monkeypatch.setenv('TRADE_PIN', PIN)
    with session_scope() as s:
        s.query(InsightSnapshot).delete()
    c = _client()
    d = c.post('/api/matrix/insights', json={'tier': 'deep', 'lang': 'es'}).get_json()
    assert tiers[-1] == 'fast' and d['tier'] == 'fast' and d['tier_note_en']
    d = c.post('/api/matrix/insights', json={'tier': 'deep', 'lang': 'es'},
               headers={'X-Trade-Pin': PIN}).get_json()
    assert tiers[-1] == 'deep' and 'tier_note' not in d
    # un viaje en el tiempo NO deja fila en el historial; el estado actual sí
    with session_scope() as s:
        s.query(InsightSnapshot).delete()
    c.post('/api/matrix/insights', json={'as_of': '2020-05-01', 'lang': 'es'})
    c.post('/api/matrix/insights', json={'as_of': '2020-05-02', 'lang': 'xx'})
    with session_scope() as s:
        assert s.query(InsightSnapshot).count() == 0
    M._TTL_CACHE.clear()                                          # (la lectura 'es' de arriba estaba en caché)
    c.post('/api/matrix/insights', json={'lang': 'zz'})            # idioma raro → 'es'
    with session_scope() as s:
        rows = s.query(InsightSnapshot).all()
        assert len(rows) == 1 and rows[0].lang == 'es'
    # pasado el presupuesto de IA por IP: plantilla, sin cachear ni guardar
    monkeypatch.setattr(M, '_TTL_CACHE', {})
    from core import http as h
    with h._rate_lock:
        h._rate_buckets['127.0.0.1:matrix_insights_ai'] = [time.time()] * 50
    n = len(tiers)
    d = c.post('/api/matrix/insights', json={'lang': 'en'}).get_json()
    assert d['model'] == 'plantilla' and len(tiers) == n and d['insights']
    assert not any(k.startswith('insights:') for k in M._TTL_CACHE)


@needs_db
def test_aprobar_a_mano_mientras_corre_el_radar_da_409(db, monkeypatch, clean_limits):
    """#22 residual: auto_cycle aún lee-y-luego-escribe; mientras corre, una
    propuesta que PODRÍA auto-aplicar no se resuelve a mano (evita la doble
    ejecución). Las que el ciclo no toca siguen funcionando."""
    import ontology.api as oapi
    monkeypatch.delenv('TRADE_PIN', raising=False)
    monkeypatch.setitem(oapi._cycle_state, 'running', True)
    c = _client()
    pid = _new_proposal()                                   # AnotarObjeto, confianza 0.9
    r = c.post(f'/api/ontology/agents/proposals/{pid}/approve', json={'actor': 'ana'})
    assert r.status_code == 409 and r.get_json()['code'] == 'cycle_running' and r.get_json()['error_en']
    assert c.post(f'/api/ontology/agents/proposals/{pid}/reject', json={'actor': 'ana'}).status_code == 409
    assert _status(pid) == 'pending'
    otra = _new_proposal(payload={'object_id': 'INF_A', 'decision': 'x'}, action_type='RegistrarDecision')
    r = c.post(f'/api/ontology/agents/proposals/{otra}/reject', json={'actor': 'ana'})
    assert r.status_code == 200
    monkeypatch.setitem(oapi._cycle_state, 'running', False)
    r = c.post(f'/api/ontology/agents/proposals/{pid}/approve', json={'actor': 'ana'})
    assert r.status_code == 200, r.get_json()
