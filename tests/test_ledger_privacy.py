"""tests/test_ledger_privacy.py — INFRA_OPERATIVA paso 6, §2.7: nunca texto personal en claro en el libro.

Garantiza:
  · el texto personal (mensaje del chat, nota de un usuario) registrado con `ctx.private_text` NO aparece en
    ninguna fila (decisions, decision_refs, decision_outcomes) ni en ningún blob (descomprimido): solo su
    HMAC-SHA256 con clave derivada (HKDF de SECRET_KEY) + key_id + largo + idioma;
  · el HMAC es estable (mismo texto + misma clave → mismo valor), cambia con SECRET_KEY y el key_id no revela
    la clave; en producción con la SECRET_KEY por defecto NO se calcula (sería forjable): privacy_key_weak;
  · el dueño y la IP van siempre como hash (core/identity.hash_id);
  · el error de una entrada inválida no copia los valores de entrada (Pydantic los incluye en sus errores);
  · /api/ledger sin PIN no devuelve la etiqueta libre, el sujeto ni el manifiesto.
"""
import json
import os
import sys
import zlib

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
SECRET_TEXT = 'Mi cuenta personal tiene 48.250 USD y vivo en Calle Falsa 123'
PROD_VARS = ('RAILWAY_ENVIRONMENT', 'RAILWAY_ENVIRONMENT_NAME', 'RAILWAY_PROJECT_ID')


@pytest.fixture
def dev(monkeypatch):
    for v in PROD_VARS:
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv('SECRET_KEY', 'clave-de-prueba-larga-y-unica-91')


def test_hmac_estable_con_key_id_y_dependiente_de_la_clave(dev, monkeypatch):
    from core import decisions
    a = decisions.pii_hmac(SECRET_TEXT, 'es')
    b = decisions.pii_hmac(SECRET_TEXT, 'es')
    assert a == b and set(a) == {'hmac', 'key_id', 'len', 'lang'} and a['len'] == len(SECRET_TEXT)
    assert SECRET_TEXT not in json.dumps(a)
    k, key_id, weak = decisions.pii_key()
    assert not weak and key_id == a['key_id'] and k.hex() not in key_id and 'clave-de-prueba' not in key_id
    assert decisions.pii_hmac(SECRET_TEXT + '.')['hmac'] != a['hmac']
    monkeypatch.setenv('SECRET_KEY', 'otra-clave-distinta-55')
    c = decisions.pii_hmac(SECRET_TEXT, 'es')
    assert c['hmac'] != a['hmac'] and c['key_id'] != a['key_id']


def test_produccion_con_clave_por_defecto_no_calcula_hmac(monkeypatch):
    from core import decisions
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.setenv('RAILWAY_ENVIRONMENT', 'production')
    d = decisions.pii_hmac(SECRET_TEXT)
    assert d == {'len': len(SECRET_TEXT), 'privacy_key_weak': True}


def test_dueno_e_ip_como_hash(dev):
    from core import identity
    h = identity.hash_id('owner-xyz-123', 'owner')
    assert h and len(h) == 16 and 'owner-xyz' not in h
    assert identity.hash_id('owner-xyz-123', 'owner') == h and identity.hash_id('owner-xyz-123', 'ip') != h
    p = identity.anon('chat', owner='owner-xyz-123')
    assert 'owner-xyz-123' not in json.dumps(p.as_dict())


def test_error_de_validacion_sin_valores_de_entrada():
    from pydantic import BaseModel, ValidationError

    from core.decisions import safe_error

    class M(BaseModel):
        n: int
    try:
        M(n=SECRET_TEXT)
    except ValidationError as e:
        out = safe_error(e)
    assert out['code'] == 'invalid_input' and out['errors'][0]['loc'] == ['n']
    assert SECRET_TEXT not in json.dumps(out)


@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    yield engine
    Base.metadata.drop_all(engine)


@needs_db
def test_texto_personal_no_aparece_en_ninguna_fila_ni_blob(db, dev):
    from sqlalchemy import text

    from core import decisions, identity
    from ontology.db import session_scope
    p = identity.anon('chat', declared=None, owner='owner-abc-777')
    with session_scope() as s:
        with decisions.decision_scope('chat.answer', p, session=s, durability='sync',
                                      subject={'entity_ids': ['NVDA']}) as ctx:
            ctx.private_text('message', SECRET_TEXT, 'es')
            ctx.evidence('tool_result', 'get_company:req1', ref_hash='a' * 64)
            ctx.output = {'answer_sha': decisions.sha256_hex({'a': 'respuesta'}), 'agents_used': ['cadena']}
            ctx.status = 'answered'
        did = ctx.id
    # también por el camino async (sesión autónoma)
    with session_scope() as s:
        with decisions.decision_scope('chat.route', p, session=s) as ctx2:
            ctx2.private_text('message', SECRET_TEXT)
            ctx2.status = 'recorded'
    with db.connect() as c:
        dump = ' '.join(json.dumps(r[0], ensure_ascii=False) for r in c.execute(text(
            'SELECT to_jsonb(t) FROM decisions t UNION ALL SELECT to_jsonb(t) FROM decision_refs t '
            'UNION ALL SELECT to_jsonb(t) FROM decision_outcomes t')))
        blobs = [zlib.decompress(bytes(b)).decode('utf-8') for (b,) in c.execute(text(
            'SELECT body FROM decision_blobs WHERE body IS NOT NULL'))]
    for frag in (SECRET_TEXT, 'Calle Falsa', '48.250', 'owner-abc-777'):
        assert frag not in dump, frag
        assert all(frag not in b for b in blobs), frag
    with session_scope() as s:
        d = decisions.get(s, did, redact=False)
        r2 = decisions.get(s, ctx2.id, redact=False)
    priv = d['manifest']['privacy']['message']
    assert priv == decisions.pii_hmac(SECRET_TEXT, 'es')
    assert r2['durability'] == 'async' and r2['manifest']['privacy']['message']['hmac'] == priv['hmac']
    assert d['on_behalf_of'].startswith('owner:')


@needs_db
def test_api_sin_pin_no_devuelve_etiqueta_sujeto_ni_manifiesto(db, dev, monkeypatch):
    from flask import Flask

    from core import decisions, identity
    from core import http as h
    from core import pin
    from core.ledger_api import ledger_bp
    from ontology.db import session_scope
    pin._reset_for_tests()
    with h._rate_lock:
        h._rate_buckets.clear()
    monkeypatch.setenv('TRADE_PIN', 'pin-privacidad-3')
    with session_scope() as s:
        with decisions.decision_scope('ontology.action', identity.operator('ui', 'Nombre Personal'), session=s,
                                      subject={'entity_ids': ['EMPRESA_X']}) as ctx:
            ctx.payload_blob({'texto': 'contenido del operador'})
            ctx.output = {'ok': True}
    app = Flask('privacy_api')
    app.register_blueprint(ledger_bp)
    c = app.test_client()
    body = c.get(f'/api/ledger/decision/{ctx.id}').get_data(as_text=True)
    lst = c.get('/api/ledger/decisions').get_data(as_text=True)
    for frag in ('Nombre Personal', 'EMPRESA_X', 'contenido del operador', 'manifest"', 'subject'):
        assert frag not in body and frag not in lst, frag
    # y el filtro por entidad no sirve para sondear sin PIN
    assert json.loads(c.get('/api/ledger/decisions?entity=EMPRESA_X').get_data())['count'] >= 1
    pin._reset_for_tests()


@needs_db
def test_fichas_reales_de_chat_y_jev_sin_texto_en_claro(db, dev):
    """Paso 20: las fichas que escriben los sitios REALES (khipu_chat.ledger_answer, decide.ledger_route) guardan el
    mensaje solo como HMAC, los argumentos de las herramientas (que pueden repetir la pregunta) solo como huella y la
    clave de la sombra de Jev como 'hmac:…'."""
    import uuid

    from sqlalchemy import text

    from core import decide, decisions, identity
    from core import khipu_chat as kc
    p = identity.anon('chat', owner='owner-abc-777')
    out = {'answer': 'Respuesta pública de la IA.', 'answer_source': 'ai', 'model': 'claude-x', 'steps': 2,
           'req_id': 'req-priv-1', 'sources': [{'label': 'Yahoo Finance', 'as_of': '2026-10-13T10:00:00Z'}],
           'tools_used': [{'name': 'web_search', 'args_summary': SECRET_TEXT, 'ok': True, 'ms': 12}],
           'agents_used': [{'agent': 'radar', 'tools': ['web_search'], 'ok': True}], 'entities': [{'id': 'NVDA'}]}
    did = uuid.uuid4()
    assert kc.ledger_answer(did, p, SECRET_TEXT, 'es', out, [])
    assert decide.ledger_route({'route': 'needs_tools', 'confidence': 0.9}, {'route': 'needs_tools'}, True,
                               SECRET_TEXT, None, 'req-priv-1')
    key = decide.private_key(SECRET_TEXT)
    assert key.startswith('hmac:') and SECRET_TEXT[:10] not in key
    decisions.flush_async(timeout=10)
    with db.connect() as c:
        rows = c.execute(text("SELECT to_jsonb(t) FROM decisions t WHERE kind IN ('chat.answer', 'chat.route') "
                              "AND correlation_id = 'req-priv-1'")).all()
        dump = ' '.join(json.dumps(r[0], ensure_ascii=False) for r in rows)
        blobs = [zlib.decompress(bytes(b)).decode('utf-8') for (b,) in c.execute(text(
            'SELECT body FROM decision_blobs WHERE body IS NOT NULL'))]
    assert len(rows) == 2
    for frag in (SECRET_TEXT, 'Calle Falsa', '48.250', 'owner-abc-777'):
        assert frag not in dump, frag
        assert all(frag not in b for b in blobs), frag
    assert decisions.pii_hmac(SECRET_TEXT, 'es')['hmac'] in dump
