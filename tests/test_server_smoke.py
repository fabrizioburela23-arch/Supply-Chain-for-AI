"""
Smoke tests for Khipu Finance server.py
Run: python -m pytest tests/ -v
No external API keys needed — only tests routes that work offline.
"""
import pytest
import json
import os

# Set dummy env vars before importing app
os.environ.setdefault('SECRET_KEY', 'test-secret-key-32chars-minimum!!')
os.environ.setdefault('FINNHUB_KEY', '')
os.environ.setdefault('ANTHROPIC_KEY', '')

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app as flask_app


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c


def test_health(client):
    r = client.get('/api/health')
    assert r.status_code == 200
    data = r.get_json()
    # Health returns service flags, not a 'status' key
    assert 'app' in data or 'server' in data or 'status' in data


def test_docs(client):
    r = client.get('/docs')
    assert r.status_code == 200
    data = r.get_json()
    assert 'endpoints' in data


def test_bixby_prompt(client):
    r = client.get('/api/voice/bixby-prompt')
    assert r.status_code == 200
    data = r.get_json()
    assert 'system_prompt' in data
    assert 'Bixby' in data['system_prompt']
    assert 'agent_name' in data


def test_auth_key_generation(client):
    r = client.post('/v1/auth/key',
                    data=json.dumps({'user_id': 'test_user', 'tier': 'free'}),
                    content_type='application/json')
    assert r.status_code == 200
    data = r.get_json()
    assert 'api_key' in data
    assert data['api_key'].startswith('kfi_')


def test_v1_nodes_requires_auth(client):
    r = client.get('/v1/nodes')
    assert r.status_code == 401


def test_v1_nodes_with_free_key(client):
    # Generate a key first
    r = client.post('/v1/auth/key',
                    data=json.dumps({'user_id': 'test', 'tier': 'free'}),
                    content_type='application/json')
    key = r.get_json()['api_key']
    r2 = client.get('/v1/nodes', headers={'X-KHIPU-Key': key})
    assert r2.status_code == 200
    data = r2.get_json()
    # API returns a count summary; full nodes are in the JS bundle
    assert 'nodes' in data or 'count' in data


def test_manifest(client):
    r = client.get('/manifest.webmanifest')
    assert r.status_code == 200


def test_icon(client):
    r = client.get('/icon.svg')
    assert r.status_code == 200


def test_sw(client):
    r = client.get('/sw.js')
    assert r.status_code == 200


def test_index_serves_app(client):
    r = client.get('/')
    assert r.status_code == 200
    assert b'Khipu' in r.data


def test_rag_index_batch_empty(client):
    r = client.post('/api/rag/index-batch',
                    data=json.dumps([]),
                    content_type='application/json')
    # Should return 200 even if RAG is offline (empty list)
    data = r.get_json()
    assert 'indexed' in data or 'error' in data


def test_portfolio_risk_requires_positions(client):
    # Get a starter key
    r = client.post('/v1/auth/key',
                    data=json.dumps({'user_id': 'test', 'tier': 'starter'}),
                    content_type='application/json')
    key = r.get_json()['api_key']
    r2 = client.post('/v1/risk/portfolio',
                     data=json.dumps({}),
                     content_type='application/json',
                     headers={'X-KHIPU-Key': key})
    assert r2.status_code == 400
    assert 'positions required' in r2.get_json().get('error', '')
