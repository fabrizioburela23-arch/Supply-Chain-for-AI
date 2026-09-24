"""
tests/test_server_smoke.py — Khipu Finance smoke tests
No API keys required. Tests structure and static responses only.
Run: pytest tests/ -v
"""
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('FINNHUB_KEY', '')
os.environ.setdefault('FMP_KEY', '')
os.environ.setdefault('ANTHROPIC_KEY', '')
os.environ.setdefault('AV_KEY', '')
os.environ.setdefault('MARKETSTACK_KEY', '')

import server  # noqa: E402


@pytest.fixture(scope='module')
def client():
    server.app.config['TESTING'] = True
    with server.app.test_client() as c:
        yield c


# ── Static file routes ─────────────────────────────────────────────────────

def test_index_returns_html(client):
    r = client.get('/')
    assert r.status_code == 200
    assert b'<!DOCTYPE html>' in r.data or b'Khipu' in r.data


def test_service_worker_js(client):
    r = client.get('/sw.js')
    assert r.status_code == 200
    assert b'cache' in r.data.lower() or b'Cache' in r.data


def test_manifest(client):
    r = client.get('/manifest.webmanifest')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert 'name' in data or 'short_name' in data


def test_icon_svg(client):
    r = client.get('/icon.svg')
    assert r.status_code == 200
    assert r.content_type.startswith('image/svg')


# ── Health endpoint ────────────────────────────────────────────────────────

def test_health(client):
    r = client.get('/api/health')
    assert r.status_code == 200
    data = json.loads(r.data)
    # Health returns service status flags (not a simple 'status':'ok')
    assert 'app' in data or 'server' in data or 'finnhub' in data


def test_health_has_app_name(client):
    r = client.get('/api/health')
    data = json.loads(r.data)
    assert data.get('app')  # el nombre de marca puede cambiar; solo validamos que exista


# ── Quote endpoints (no key → 400 error JSON, not crash) ──────────────────

def test_quote_no_key_returns_json(client):
    r = client.get('/api/quote/NVDA')
    # Without FINNHUB_KEY, server returns 400 with JSON error
    assert r.status_code in (200, 400, 503)
    assert r.content_type.startswith('application/json')


def test_batch_quotes_no_key_returns_json(client):
    r = client.get('/api/quotes?tickers=NVDA,AMD')
    assert r.status_code in (200, 400, 503)
    assert r.content_type.startswith('application/json')


# ── News / GDELT ───────────────────────────────────────────────────────────

def test_gdelt_returns_json(client):
    r = client.get('/api/news/gdelt/Nvidia')
    assert r.status_code in (200, 503)
    assert r.content_type.startswith('application/json')


# ── Space launches ──────────────────────────────────────────────────────────

def test_space_launches_json(client):
    r = client.get('/api/space/launches')
    # External launch library API — may be unavailable in test env
    assert r.status_code in (200, 502, 503)
    assert r.content_type.startswith('application/json')


# ── Khipu voice prompt ─────────────────────────────────────────────────────

def test_bixby_prompt_returns_text(client):
    r = client.get('/api/voice/bixby-prompt')
    assert r.status_code == 200
    assert len(r.data) > 50


# ── AI analyze (no key → JSON error, not crash) ────────────────────────────

def test_ai_analyze_no_key(client):
    payload = {'node_id': 'Nvidia', 'label': 'Nvidia', 'cat': 'fabless'}
    r = client.post('/api/ai/analyze', json=payload)
    assert r.status_code in (200, 400, 503)
    assert r.content_type.startswith('application/json')


# ── RAG proxy eliminado (Etapa 1) — la ruta ya no debe existir ─────────────

def test_rag_proxy_removed(client):
    r = client.get('/api/rag/stats')
    assert r.status_code == 404


# ── VaR / CVaR portfolio risk (JWT-protected in production) ───────────────

def test_var_endpoint_requires_auth(client):
    # /v1/risk/portfolio requires a valid JWT — 401 without one
    r = client.post('/v1/risk/portfolio', json={})
    assert r.status_code in (400, 401, 403)
    assert r.content_type.startswith('application/json')


def test_var_endpoint_with_no_av_key(client):
    payload = {'positions': {'NVDA': {'shares': 10, 'buy_price': 100.0}}}
    r = client.post('/v1/risk/portfolio', json=payload)
    assert r.status_code in (200, 401, 403, 503)
    assert r.content_type.startswith('application/json')


# ── Docs endpoint ──────────────────────────────────────────────────────────

def test_docs_returns_json(client):
    r = client.get('/docs')
    assert r.status_code == 200
    assert r.content_type.startswith('application/json')


# ── Node / engine files exist ─────────────────────────────────────────────

def test_static_node_files_exist():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for fname in ['nodes/nodes_expand.js',
                  'nodes/nodes_expand2.js', 'nodes/links_expand.js']:
        path = os.path.join(base, fname)
        assert os.path.exists(path), f"Missing: {fname}"
        assert os.path.getsize(path) > 100, f"Empty: {fname}"


def test_engine_files_exist():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for fname in ['engine/graph3d.js', 'engine/hypergraph.js',
                  'engine/voice.js', 'engine/secondbrain.js']:
        path = os.path.join(base, fname)
        assert os.path.exists(path), f"Missing: {fname}"


def test_ai_error_hint_es_accionable():
    """Un '404' pelado no le dice a nadie qué hacer. Los proveedores retiran
    modelos (sept-2026: gemini-2.0-flash 404 y llama-3.1-70b 410 a la vez,
    dejando la app sin respaldo justo cuando Claude se quedó sin saldo).
    El 🩺 debe nombrar la variable de entorno que lo arregla."""
    from server import _ai_error_hint as hint

    retirado = hint('Gemini HTTP 404', 'gemini-2.5-flash', 'GEMINI_MODEL')
    assert 'GEMINI_MODEL' in retirado and 'retirado' in retirado
    assert 'gemini-2.5-flash' in retirado

    assert 'NVIDIA_MODEL' in hint('NVIDIA HTTP 410', 'm', 'NVIDIA_MODEL')

    saldo = hint('Error code: 400 — your credit balance is too low', 'm', 'X')
    assert 'aldo' in saldo  # "saldo agotado"

    assert 'ímite' in hint('HTTP 429 quota exceeded', 'm', 'X')      # límite
    assert 'key' in hint('401 unauthorized', 'm', 'X').lower()

    # sin pista reconocible NO se inventa una explicación
    assert hint('algo completamente inesperado', 'm', 'X') == ''


def test_db_error_hint_es_accionable():
    """Un traceback de psycopg2 no le dice a nadie qué hacer. Caso real
    (sept-2026): DATABASE_URL apuntaba a 'postgres.railway.internal' pero el
    servicio ya no existía con ese nombre, y el panel solo mostraba el error
    crudo. El 🩺 debe nombrar la solución: variable como REFERENCIA."""
    from server import _db_error_hint as hint

    railway = hint('could not translate host name "postgres.railway.internal" '
                   'to address: Name or service not known')
    assert 'REFERENCIA' in railway
    assert 'DATABASE_URL' in railway

    # un host que no resuelve pero no es Railway → pista genérica, no la de Railway
    neo = hint('Failed to DNS resolve address a83aa2de.databases.neo4j.io:7687: '
               'Name or service not known')
    assert 'no resuelve' in neo
    assert 'REFERENCIA' not in neo

    assert 'credenciales' in hint('FATAL: password authentication failed for user "postgres"')
    assert 'apagado' in hint('connection refused')
    assert 'espera' in hint('connection timed out')

    # sin pista reconocible NO se inventa una explicación
    assert hint('algo completamente inesperado') == ''


def test_la_vista_3d_temporal_es_pequena_por_construccion():
    """El 3D temporal (engine/timeline3d.js) solo dibuja hechos CON fecha real
    y las empresas que participan en ellos — no las 949 del mapa. Esa es la
    razón de que sea barato en un teléfono, así que conviene que no se rompa
    en silencio si alguien cambia el formato de los hechos."""
    import json

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert os.path.exists(os.path.join(base, 'engine', 'timeline3d.js'))

    with open(os.path.join(base, 'data', 'grafo_v0.json'), encoding='utf-8') as fh:
        snap = json.load(fh)

    situables = [f for f in (snap.get('temporal_facts') or [])
                 if f.get('object_type') == 'node' and f.get('valid_from')
                 and f.get('subject') and f.get('object')
                 and f.get('subject') != f.get('object')]
    entidades = {e for f in situables for e in (f['subject'], f['object'])}

    assert len(situables) >= 60, f'solo {len(situables)} hechos fechados: el eje temporal se queda vacío'
    # Cota de coste: ~20 vértices por cuerda + 2 por columna. Si esto crece
    # mucho habrá que agrupar por año en vez de dibujar cada hecho.
    vertices = len(situables) * 20 + len(entidades) * 2
    assert vertices < 40000, f'{vertices} vértices — la escena dejó de ser trivial, revisar LOD'


def test_timeline3d_degrada_sin_webgl():
    """Sin WebGL o sin hechos fechados debe decirlo en texto, no romper la
    pestaña ni dejar un hueco mudo."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, 'engine', 'timeline3d.js'), encoding='utf-8') as fh:
        src = fh.read()
    assert 'if (!window.THREE)' in src
    assert 'No hay hechos con fecha real' in src
    assert 'needs WebGL' in src          # y en inglés (regla bilingüe)
