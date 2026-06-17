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
    assert data.get('app') == 'Khipu Finance'


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


# ── Bixby voice prompt ─────────────────────────────────────────────────────

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


# ── RAG proxy (service not running → graceful JSON error) ─────────────────

def test_rag_stats_graceful(client):
    r = client.get('/api/rag/stats')
    assert r.status_code in (200, 500, 502, 503)
    assert r.content_type.startswith('application/json')


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
    for fname in ['nodes/nodes_core.js', 'nodes/nodes_expand.js',
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
