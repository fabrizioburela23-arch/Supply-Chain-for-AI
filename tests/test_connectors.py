"""tests/test_connectors.py — 🧩 Conectores (Composio): una puerta a las apps de cada persona.

Se blinda: leer es directo; ESCRIBIR nunca ocurre desde el chat (queda pendiente hasta clic + PIN); cada persona solo ve
y confirma lo suyo; el modelo no puede elegir de quién son las apps; confirmar deja decisión en el libro; lo de las apps
llega marcado como contenido externo; sin clave de Composio todo queda apagado.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from core import connectors as C  # noqa: E402

KEY_A = 'a' * 32
KEY_B = 'b' * 32


class _Resp:
    def __init__(self, status, data):
        self.status_code, self._d = status, data

    def json(self):
        return self._d


class FakeHTTP:
    def __init__(self):
        self.calls = []

    def request(self, method, url, params=None, json=None, timeout=None, headers=None):
        self.calls.append((method, url.split('/api/v3.1')[-1], params, json, headers))
        path = url.split('/api/v3.1')[-1]
        if path == '/tools':
            return _Resp(200, {'items': [
                {'slug': 'GMAIL_FETCH_EMAILS', 'name': 'Fetch emails', 'description': 'List emails',
                 'toolkit': {'slug': 'gmail'}, 'input_parameters': {'properties': {'query': {'type': 'string'}}}},
                {'slug': 'GMAIL_SEND_EMAIL', 'name': 'Send email', 'description': 'Send',
                 'toolkit': {'slug': 'gmail'}, 'input_parameters': {'properties': {'to': {'type': 'string'},
                                                                                   'body': {'type': 'string'}},
                                                                    'required': ['to']}},
                {'slug': 'bad slug!', 'toolkit': {'slug': 'x'}}]})
        if path == '/connected_accounts':
            return _Resp(200, {'items': [{'toolkit': {'slug': 'gmail'}, 'status': 'ACTIVE'}]})
        if path == '/auth_configs' and method == 'GET':
            return _Resp(200, {'items': []})
        if path == '/auth_configs' and method == 'POST':
            return _Resp(201, {'auth_config': {'id': 'ac_1'}})
        if path == '/connected_accounts/link':
            return _Resp(201, {'redirect_url': 'https://connect.composio.dev/x', 'expires_at': 'later'})
        if path.startswith('/tools/execute/'):
            return _Resp(200, {'successful': True, 'data': {'messages': [{'subject': 'hola'}]}, 'error': None})
        return _Resp(404, {'error': {'message': 'nope'}})


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('COMPOSIO_API_KEY', 'test-key')
    monkeypatch.setattr(C, '_PENDING', {})
    monkeypatch.setattr(C, '_AUTH_CFG', {})


def test_write_detection_is_conservative():
    assert not C.is_write('GMAIL_FETCH_EMAILS') and not C.is_write('GOOGLECALENDAR_LIST_EVENTS')
    for s in ('GMAIL_SEND_EMAIL', 'GOOGLESHEETS_BATCH_UPDATE', 'SLACK_POST_MESSAGE', 'NOTION_CREATE_PAGE',
              'GOOGLEDRIVE_DELETE_FILE', 'WEIRD_THING'):       # lo desconocido = escribe (pedir confirmación)
        assert C.is_write(s), s


def test_user_id_is_opaque_and_per_person():
    a, b = C.user_id(KEY_A), C.user_id(KEY_B)
    assert a.startswith('kh_') and a != b and KEY_A not in a and C.user_id(KEY_A) == a
    assert C.user_id('short') is None and C.user_id(None) is None


def test_disabled_without_key(monkeypatch):
    monkeypatch.delenv('COMPOSIO_API_KEY')
    assert not C.enabled()
    with pytest.raises(C.ConnectorError):
        C.search_tools('emails')


def test_rest_calls_use_v31_and_api_key_header():
    h = FakeHTTP()
    tools = C.search_tools('emails', 'gmail', http=h)
    assert [t['tool'] for t in tools] == ['GMAIL_FETCH_EMAILS', 'GMAIL_SEND_EMAIL']
    assert tools[1]['changes_something'] and 'to:string' in tools[1]['params'] and 'body?:string' in tools[1]['params']
    m, path, params, body, headers = h.calls[0]
    assert m == 'GET' and path == '/tools' and params['query'] == 'emails' and params['toolkit_slug'] == 'gmail'
    assert headers['x-api-key'] == 'test-key'
    uid = C.user_id(KEY_A)
    assert C.connections(uid, http=h) == {'gmail': 'ACTIVE'}
    link = C.connect_link(uid, 'gmail', http=h)
    assert link['redirect_url'].startswith('https://')
    assert [c[1] for c in h.calls[-3:]] == ['/auth_configs', '/auth_configs', '/connected_accounts/link']
    assert h.calls[-1][3] == {'auth_config_id': 'ac_1', 'user_id': uid}
    res = C.execute(uid, 'GMAIL_FETCH_EMAILS', {'query': 'x'}, http=h)
    assert res['ok'] and 'hola' in res['data']


def test_pending_is_per_person_single_use_and_bounded():
    a, b = C.user_id(KEY_A), C.user_id(KEY_B)
    pid = C.propose(a, 'GMAIL_SEND_EMAIL', 'gmail', {'to': 'x@y.z'}, 'enviar')
    assert [p['id'] for p in C.pending(a)] == [pid] and C.pending(b) == []
    assert C.take(b, pid) is None                    # otra persona no puede confirmarla
    assert C.take(a, pid)['tool'] == 'GMAIL_SEND_EMAIL' and C.take(a, pid) is None
    for i in range(8):
        C.propose(a, 'GMAIL_SEND_EMAIL', 'gmail', {}, f'n{i}')
    assert len(C.pending(a)) == 5


def test_chat_tools_never_write_and_mark_external(monkeypatch):
    from core import khipu_chat as kc
    calls = []
    monkeypatch.setattr(C, 'execute', lambda uid, slug, args, http=None: calls.append(slug) or {'ok': True, 'data': '{"x":1}', 'error': None})
    uid = C.user_id(KEY_A)
    w = kc.x_apps_run('gmail_send_email', {'to': 'x@y.z', 'body': 'hola'}, 'Enviar hola a x', apps_user=uid)
    assert w['status'] == 'waiting_for_user_confirmation' and calls == []
    assert C.pending(uid)[0]['summary'] == 'Enviar hola a x'
    r = kc.x_apps_run('GMAIL_FETCH_EMAILS', {'query': 'x'}, apps_user=uid)
    assert calls == ['GMAIL_FETCH_EMAILS'] and r['untrusted_external_content'] is True
    with pytest.raises(kc.ToolFailure):
        kc.x_apps_run('GMAIL_FETCH_EMAILS', {}, apps_user=None)


def test_model_cannot_choose_whose_apps():
    from core import khipu_chat as kc
    out = kc._server_args('apps_run', {'tool': 'X', 'apps_user': 'kh_victim'}, {'apps_user': 'kh_me'})
    assert out['apps_user'] == 'kh_me'
    assert kc._server_args('apps_search', {'query': 'q', 'apps_user': 'kh_victim'}, {})['apps_user'] is None


def test_validate_request_sets_person_from_browser_key():
    from flask import Flask

    from core import khipu_chat as kc
    app = Flask('t')
    with app.test_request_context(headers={'X-Khipu-Owner': KEY_A}):
        req = kc.validate_request({'message': 'lee mis correos', 'context': {'apps_user': 'kh_victim'}})
    assert req['context']['apps_user'] == C.user_id(KEY_A)


def _client():
    from flask import Flask

    from core.connectors_api import connectors_bp
    app = Flask('connectors')
    app.register_blueprint(connectors_bp)
    return app.test_client()


def test_confirm_needs_pin_and_owner(monkeypatch):
    monkeypatch.setenv('TRADE_PIN', '4321')
    c = _client()
    pid = C.propose(C.user_id(KEY_A), 'GMAIL_SEND_EMAIL', 'gmail', {'to': 'x'}, 'enviar')
    r = c.post('/api/connectors/confirm', json={'id': pid}, headers={'X-Khipu-Owner': KEY_A})
    assert r.status_code in (401, 403)                      # sin PIN: nada
    r = c.post('/api/connectors/confirm', json={'id': pid}, headers={'X-Khipu-Owner': KEY_B, 'X-Trade-Pin': '4321'})
    assert r.status_code == 404                              # otra persona: no existe para ella
    assert len(C.pending(C.user_id(KEY_A))) == 1
    r = c.get('/api/connectors/pending', headers={'X-Khipu-Owner': KEY_A})
    assert r.get_json()['enabled'] and r.get_json()['pending'][0]['id'] == pid
    assert c.post('/api/connectors/discard', json={'id': pid}, headers={'X-Khipu-Owner': KEY_A}).get_json()['ok']


@pytest.mark.skipif(not os.getenv('DATABASE_URL'), reason='requiere DATABASE_URL (Postgres)')
def test_confirm_leaves_decision_then_executes(monkeypatch):
    monkeypatch.setenv('TRADE_PIN', '4321')
    from ontology.db import init_schema
    assert init_schema(retries=1)
    done = []
    monkeypatch.setattr(C, 'execute', lambda uid, slug, args, http=None: done.append((slug, args)) or {'ok': True, 'data': 'ok', 'error': None})
    pid = C.propose(C.user_id(KEY_A), 'GMAIL_SEND_EMAIL', 'gmail', {'to': 'x@y.z', 'body': 'secreto'}, 'enviar')
    r = _client().post('/api/connectors/confirm', json={'id': pid}, headers={'X-Khipu-Owner': KEY_A, 'X-Trade-Pin': '4321'})
    assert r.status_code == 200 and r.get_json()['ok'], r.get_json()
    assert done == [('GMAIL_SEND_EMAIL', {'to': 'x@y.z', 'body': 'secreto'})]
    from core import decisions
    from ontology.db import session_scope
    with session_scope() as s:
        rows = [d for d in decisions.list_decisions(s, redact=False, limit=50) if d['kind'] == 'policy.change']
    doc = str(rows[0])
    assert 'connectors.execute' in doc and 'GMAIL_SEND_EMAIL' in doc and 'secreto' not in doc   # el contenido no va al libro


def test_wired_in_ui():
    html = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    assert 'engine/connectors.js' in html
    assert "'/engine/connectors.js'" in open(os.path.join(ROOT, 'sw.js'), encoding='utf-8').read()
    ck = open(os.path.join(ROOT, 'engine/cockpit.js'), encoding='utf-8').read()
    assert "id: 'apps'" in ck and 'KhipuConnectors.open' in ck
    js = open(os.path.join(ROOT, 'engine/connectors.js'), encoding='utf-8').read()
    assert "_tradeFetch" in js and '/api/connectors/confirm' in js
