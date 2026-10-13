"""tests/test_rutas_acceso_decision.py — lote I1 (Fase 2+): las últimas rutas de escritura fuera de la voz dejan
su decisión (docs/CIERRE_INFRA.md §3; tests/test_cierre_infra.py SIN_DECISION solo se achica):

  POST /api/mcp/tokens · /api/mcp/tokens/<id>/revoke   → policy.change (mcp.tokens), sync, misma transacción
  POST /oauth/register|authorize|token|revoke          → policy.change (mcp.oauth); la rotación del refresh, async
  POST /api/sim/agents                                 → whatif.agent_sim (async, después de responder)

Y lo que NUNCA debe quedar en el libro: el token en claro, el refresh token, el secreto del cliente ni el código
de autorización. Sin libro (base caída) el token NO se crea (503 ledger_unavailable).

Sin red y sin IA. Base propia (drop/create como test_mcp.py).
"""
import base64
import hashlib
import json
import os
import re
import sys
import zlib
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
PIN = '4321'


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('TRADE_PIN', PIN)
    for k in ('MCP_ENABLED', 'MCP_OAUTH_ENABLED', 'MCP_PUBLIC_URL', 'MCP_STATIC_TOKEN', 'MCP_PIN_MAX_FAILS'):
        monkeypatch.delenv(k, raising=False)
    from core import http as _h
    from mcp_server import auth as _a
    _h._rate_buckets.clear()
    _a.reset_pin_guard()
    yield
    _h._rate_buckets.clear()
    _a.reset_pin_guard()


@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    import mcp_server.models  # noqa: F401
    import research.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    from flask import Flask
    from mcp_server.api import mcp_bp
    a = Flask('i1-test')
    a.config['TESTING'] = True
    a.register_blueprint(mcp_bp)
    return a.test_client()


def _pin():
    return {'X-Trade-Pin': PIN}


def _rows(kind='policy.change', policy=None):
    from sqlalchemy import text
    from core import decisions
    from ontology.db import session_scope
    decisions.flush_async(timeout=10)
    with session_scope() as s:
        rows = s.execute(text('SELECT id, kind, principal_id, subject, output, manifest, status FROM decisions '
                              'WHERE kind = :k ORDER BY seq'), {'k': kind}).mappings().all()
    out = [dict(r) for r in rows]
    if policy:
        out = [r for r in out if (r['subject'] or {}).get('policy') == policy
               or (r['output'] or {}).get('policy') == policy]
    return out


def _ledger_text():
    """Todo lo que el libro guarda (decisiones + blobs descomprimidos) como texto, para buscar secretos."""
    from sqlalchemy import text
    from core import decisions
    from ontology.db import session_scope
    decisions.flush_async(timeout=10)
    with session_scope() as s:
        rows = s.execute(text('SELECT subject, output, manifest, verdict, model FROM decisions')).all()
        blobs = s.execute(text('SELECT body FROM decision_blobs WHERE body IS NOT NULL')).all()
    parts = [json.dumps(list(r), default=str) for r in rows]
    for (b,) in blobs:
        try:
            parts.append(zlib.decompress(bytes(b)).decode('utf-8', 'replace'))
        except Exception:  # noqa: BLE001
            parts.append(bytes(b).decode('utf-8', 'replace'))
    return '\n'.join(parts)


# ── tokens MCP ───────────────────────────────────────────────────────────────
@needs_db
def test_token_create_and_revoke_leave_policy_change_without_secret(client, db):
    before = len(_rows(policy='mcp.tokens'))
    r = client.post('/api/mcp/tokens', json={'name': 'Mi Claude', 'scopes': ['read', 'research']}, headers=_pin())
    assert r.status_code == 201, r.get_json()
    tok = r.get_json()
    plain, tid = tok['token'], tok['id']
    rows = _rows(policy='mcp.tokens')
    assert len(rows) == before + 1
    d = rows[-1]
    assert d['principal_id'] == 'op:fabrizio' and d['status'] == 'executed'
    assert d['subject']['token_id'] == tid and d['subject']['action'] == 'create'
    assert d['output']['after']['scopes'] == ['read', 'research'] and d['output']['before'] is None
    # revocar: una ficha; revocar otra vez no cambia nada → ninguna ficha nueva
    assert client.post(f'/api/mcp/tokens/{tid}/revoke', json={}, headers=_pin()).status_code == 200
    assert client.post(f'/api/mcp/tokens/{tid}/revoke', json={}, headers=_pin()).status_code == 200
    rows = _rows(policy='mcp.tokens')
    assert len(rows) == before + 2
    rv = rows[-1]
    assert rv['subject']['action'] == 'revoke' and rv['output']['changed'] == ['revoked']
    assert rv['output']['before']['revoked'] is False and rv['output']['after']['revoked'] is True
    blob = _ledger_text()
    assert plain not in blob and plain[5:] not in blob
    assert hashlib.sha256(plain.encode()).hexdigest() not in blob


@needs_db
def test_token_create_without_ledger_creates_nothing(client, db, monkeypatch):
    from sqlalchemy import text
    from core import decisions
    from ontology.db import session_scope

    def _boom(*_a, **_k):
        raise RuntimeError('libro caído (simulado)')
    monkeypatch.setattr(decisions, '_insert', _boom)
    with session_scope() as s:
        n0 = s.execute(text('SELECT count(*) FROM mcp_tokens')).scalar()
    r = client.post('/api/mcp/tokens', json={'name': 'Sin libro', 'scopes': ['read']}, headers=_pin())
    assert r.status_code == 503 and r.get_json()['code'] == 'ledger_unavailable'
    assert 'token' not in r.get_json()
    with session_scope() as s:
        assert s.execute(text('SELECT count(*) FROM mcp_tokens')).scalar() == n0


@needs_db
def test_token_revoke_commits_even_when_ledger_down(client, db, monkeypatch):
    """Revisión lote I: revocar QUITA poder → nunca se bloquea por el libro (antes: 503 y el token seguía vivo)."""
    from core import decisions
    from mcp_server import auth as _a
    r = client.post('/api/mcp/tokens', json={'name': 'Filtrado', 'scopes': ['read']}, headers=_pin())
    assert r.status_code == 201
    plain, tid = r.get_json()['token'], r.get_json()['id']
    assert _a.authenticate('Bearer ' + plain) is not None

    def _boom(*_a, **_k):
        raise RuntimeError('libro caído (simulado)')
    monkeypatch.setattr(decisions, '_lineage', _boom)
    d0 = decisions.STATS['async_dropped']
    r = client.post(f'/api/mcp/tokens/{tid}/revoke', json={}, headers=_pin())
    assert r.status_code == 200, r.get_json()
    assert _a.authenticate('Bearer ' + plain) is None, 'el token filtrado sigue vivo'
    decisions.flush_async(timeout=10)
    assert decisions.STATS['async_dropped'] > d0        # la ficha perdida queda contada (🩺)


# ── OAuth ────────────────────────────────────────────────────────────────────
def _pkce():
    verifier = base64.urlsafe_b64encode(os.urandom(40)).decode().rstrip('=')
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    return verifier, challenge


def _authorize(client, cid, redirect, challenge):
    q = {'response_type': 'code', 'client_id': cid, 'redirect_uri': redirect, 'code_challenge': challenge,
         'code_challenge_method': 'S256', 'state': 's1', 'scope': 'read research', 'resource': 'http://localhost/mcp'}
    page = client.post('/oauth/authorize', data=dict(q, step='pin', pin=PIN)).get_data(as_text=True)
    consent = re.search(r'name="consent" value="([^"]*)"', page).group(1).replace('&amp;', '&')
    page = client.post('/oauth/authorize', data={'step': 'consent', 'consent': consent, 'decision': 'approve',
                                                 'scope_research': '1', 'token_name': 'Claude'}).get_data(as_text=True)
    target = re.search(r'url=([^"]+)"', page).group(1).replace('&amp;', '&')
    return parse_qs(urlparse(target).query)['code'][0]


@needs_db
def test_oauth_flow_leaves_one_decision_per_power_change_and_no_secrets(client, db):
    def n():
        return len(_rows(policy='mcp.oauth'))
    redirect = 'https://claude.ai/api/mcp/auth_callback'
    n0 = n()
    r = client.post('/oauth/register', json={'client_name': 'Claude', 'redirect_uris': [redirect],
                                             'token_endpoint_auth_method': 'client_secret_post'})
    assert r.status_code == 201
    cid, csecret = r.get_json()['client_id'], r.get_json()['client_secret']
    assert n() == n0 + 1
    reg = _rows(policy='mcp.oauth')[-1]
    assert reg['subject']['oauth_client_id'] == cid and reg['subject']['action'] == 'register'
    assert reg['output']['after']['redirect_hosts'] == ['claude.ai']
    verifier, challenge = _pkce()
    code = _authorize(client, cid, redirect, challenge)
    assert n() == n0 + 2
    auth = _rows(policy='mcp.oauth')[-1]
    assert auth['principal_id'] == 'op:fabrizio' and auth['subject']['action'] == 'authorize'
    assert sorted(auth['output']['after']['scopes']) == ['read', 'research']
    # un canje FALLIDO (PKCE mal) no da poder → ninguna ficha
    bad = client.post('/oauth/token', data={'grant_type': 'authorization_code', 'code': code, 'client_id': cid,
                                            'client_secret': csecret, 'redirect_uri': redirect,
                                            'code_verifier': 'x' * 50})
    assert bad.status_code == 400 and n() == n0 + 2
    r = client.post('/oauth/token', data={'grant_type': 'authorization_code', 'code': code, 'client_id': cid,
                                          'client_secret': csecret, 'redirect_uri': redirect,
                                          'code_verifier': verifier})
    assert r.status_code == 200, r.get_json()
    t = r.get_json()
    assert n() == n0 + 3
    tk = _rows(policy='mcp.oauth')[-1]
    assert tk['subject']['action'] == 'token' and tk['principal_id'].startswith('mcp:')
    assert tk['output']['after']['grant'] == 'authorization_code'
    r = client.post('/oauth/token', data={'grant_type': 'refresh_token', 'refresh_token': t['refresh_token'],
                                          'client_id': cid, 'client_secret': csecret})
    assert r.status_code == 200
    t2 = r.get_json()
    assert n() == n0 + 4                       # rotación: async (flush en _rows)
    assert _rows(policy='mcp.oauth')[-1]['subject']['action'] == 'refresh'
    assert client.post('/oauth/revoke', data={'token': t2['access_token'], 'client_id': cid,
                                              'client_secret': csecret}).status_code == 200
    assert n() == n0 + 5
    rv = _rows(policy='mcp.oauth')[-1]
    assert rv['subject']['action'] == 'revoke' and rv['output']['changed'] == ['revoked']
    text_all = _ledger_text()
    for secret in (csecret, code, t['access_token'], t['refresh_token'], t2['access_token'], t2['refresh_token'],
                   verifier):
        assert secret not in text_all, 'un secreto quedó en el libro'


@needs_db
def test_oauth_revoke_and_code_reuse_commit_even_when_ledger_down(client, db, monkeypatch):
    """/oauth/revoke y la revocación automática por código reutilizado se confirman sin libro (antes: rollback)."""
    from core import decisions
    from mcp_server import auth as _a
    redirect = 'https://claude.ai/api/mcp/auth_callback'
    r = client.post('/oauth/register', json={'client_name': 'Claude', 'redirect_uris': [redirect],
                                             'token_endpoint_auth_method': 'client_secret_post'})
    cid, csecret = r.get_json()['client_id'], r.get_json()['client_secret']
    tokens = []
    for _ in range(2):
        verifier, challenge = _pkce()
        code = _authorize(client, cid, redirect, challenge)
        form = {'grant_type': 'authorization_code', 'code': code, 'client_id': cid, 'client_secret': csecret,
                'redirect_uri': redirect, 'code_verifier': verifier}
        t = client.post('/oauth/token', data=form).get_json()
        assert _a.authenticate('Bearer ' + t['access_token']) is not None
        tokens.append((t, form))

    def _boom(*_a, **_k):
        raise RuntimeError('libro caído (simulado)')
    monkeypatch.setattr(decisions, '_lineage', _boom)
    (t1, _f1), (t2, f2) = tokens
    r = client.post('/oauth/revoke', data={'token': t1['access_token'], 'client_id': cid, 'client_secret': csecret})
    assert r.status_code == 200
    assert _a.authenticate('Bearer ' + t1['access_token']) is None
    r = client.post('/oauth/token', data=f2)               # el MISMO código otra vez → se revoca lo que emitió
    assert r.status_code == 400 and r.get_json()['error'] == 'invalid_grant'
    assert _a.authenticate('Bearer ' + t2['access_token']) is None


# ── simulación por agentes ───────────────────────────────────────────────────
@needs_db
def test_sim_agents_leaves_whatif_agent_sim_after_response(db, monkeypatch):
    import server
    from core import sim_agents
    monkeypatch.setattr(sim_agents, 'run', lambda scenario, seeds, lang: {
        'ok': True, 'narrative': 'n', 'model': 'stub-model', 'pct_source': 'kernel',
        'impacts': [{'id': 'TSMC', 'pct': -12.5}, {'id': 'Nvidia', 'pct': -4.0}]})
    before = len(_rows('whatif.agent_sim'))
    r = server.app.test_client().post('/api/sim/agents', json={'scenario': 'Bloqueo de Taiwán', 'seeds': ['TSMC']})
    assert r.status_code == 200 and r.get_json()['ok'] is True
    rows = _rows('whatif.agent_sim')
    assert len(rows) == before + 1
    d = rows[-1]
    assert d['subject']['entity_ids'] == ['TSMC'] and d['status'] == 'executed'
    assert d['output']['top'][0] == ['TSMC', -12.5] and d['output']['n'] == 2 and d['output']['ai_used'] is True
    assert d['output']['pct_source'] == 'kernel'
    assert d['manifest']['request_params']['endpoint'] == '/api/sim/agents'


def test_agent_sim_kind_is_in_vocabulary_and_not_replayable():
    from core import decisions, replay
    assert 'whatif.agent_sim' in decisions.KINDS
    assert decisions.default_durability('whatif.agent_sim') == 'async'
    assert not replay.replayable_kind('whatif.agent_sim')
    assert replay.kind_label('whatif.agent_sim', 'en') == 'Agent simulation'
