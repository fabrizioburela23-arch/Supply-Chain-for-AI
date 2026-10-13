"""tests/test_ops_identity.py — INFRA_OPERATIVA paso 5: QUIÉN actúa sale de la autenticación, no del texto libre.

Garantiza (docs/INFRA_OPERATIVA.md §8.1-§8.2 y §9):
  · un nombre falso en 'actor' queda SOLO como declared_name: se registra el principal (`op:fabrizio` con PIN,
    `ui:anon` sin autenticar) — antes `actor:"otra-persona-inventada"` → 200 y quedaba tal cual (G-4, GV-06);
  · en PRODUCCIÓN las escrituras de operador exigen TRADE_PIN configurado (sin él → 403); en desarrollo siguen
    abiertas (ui:anon) (G-6);
  · el canal (X-Khipu-Channel) es metadato: NO autentica (un 'mcp' o 'voice' declarado sin PIN sigue siendo
    ui:anon / 401 si hay PIN);
  · agentes solo con ids del registro único; el reloj actúa como system:<tarea>; MCP como mcp:<token_id>;
  · el cliente manda X-Khipu-Channel desde _tradeFetch (app.html), la voz ('voice') y cripto ('crypto').
"""
import os
import re
import sys
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
PIN = 'pin-identidad-4821'
PROD_VARS = ('RAILWAY_ENVIRONMENT', 'RAILWAY_ENVIRONMENT_NAME', 'RAILWAY_PROJECT_ID')


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
        return fh.read()


@pytest.fixture
def clean(monkeypatch):
    from core import http as h
    from core import pin
    for v in PROD_VARS:
        monkeypatch.delenv(v, raising=False)
    pin._reset_for_tests()
    with h._rate_lock:
        h._rate_buckets.clear()
    yield
    pin._reset_for_tests()


def _probe_app():
    """App mínima: /who (sin decorador), /op (require_operator) → devuelven el principal resuelto."""
    from flask import Flask, jsonify

    from core import identity
    from core.pin import require_operator
    app = Flask('identity_probe')

    @app.route('/who', methods=['POST'])
    def who():
        return jsonify(identity.principal_from_request(declared='otra-persona-inventada').as_dict())

    @app.route('/op', methods=['POST'])
    @require_operator
    def op():
        return jsonify(identity.principal_from_request(declared='otra-persona-inventada').as_dict())
    return app.test_client()


# ── sin base ─────────────────────────────────────────────────────────────────
def test_nombre_falso_queda_solo_como_etiqueta_y_el_pin_identifica_al_operador(monkeypatch, clean):
    monkeypatch.setenv('TRADE_PIN', PIN)
    c = _probe_app()
    d = c.post('/op', headers={'X-Trade-Pin': PIN, 'X-Khipu-Channel': 'voice', 'X-Khipu-Pin-Source': 'prompted'}).get_json()
    assert d['id'] == 'op:fabrizio' and d['kind'] == 'human' and d['auth'] == 'pin'
    assert d['declared_name'] == 'otra-persona-inventada' and d['channel'] == 'voice' and d['pin_source'] == 'prompted'
    # sin PIN → 401 (no se registra nada a nombre de nadie)
    assert c.post('/op').status_code == 401
    # una ruta SIN decorador nunca "acepta" el PIN por su cuenta (no compara, no cuenta fallos): ui:anon
    d = c.post('/who', headers={'X-Trade-Pin': PIN}).get_json()
    assert d['id'] == 'ui:anon' and d['auth'] == 'none'


def test_canal_no_es_autenticacion(monkeypatch, clean):
    monkeypatch.setenv('TRADE_PIN', PIN)
    c = _probe_app()
    for ch in ('mcp', 'voice', 'agent', 'terminal'):
        assert c.post('/op', headers={'X-Khipu-Channel': ch}).status_code == 401, ch
        d = c.post('/who', headers={'X-Khipu-Channel': ch}).get_json()
        assert d['id'] == 'ui:anon' and d['auth'] == 'none' and d['channel'] == ch
    # canal desconocido → 'api'; nunca se copia texto arbitrario
    d = c.post('/who', headers={'X-Khipu-Channel': 'root; DROP'}).get_json()
    assert d['channel'] == 'api'


def test_produccion_exige_trade_pin_configurado(monkeypatch, clean):
    monkeypatch.delenv('TRADE_PIN', raising=False)
    c = _probe_app()
    d = c.post('/op').get_json()                    # desarrollo: abierto, pero registrado como ui:anon
    assert d['id'] == 'ui:anon' and d['declared_name'] == 'otra-persona-inventada'
    monkeypatch.setenv('RAILWAY_ENVIRONMENT', 'production')
    r = c.post('/op')
    assert r.status_code == 403 and r.get_json()['code'] == 'trading_disabled'


def test_dueno_y_etiqueta_saneados(monkeypatch, clean):
    monkeypatch.delenv('TRADE_PIN', raising=False)
    c = _probe_app()
    d = c.post('/who', headers={'X-Khipu-Owner': 'owner-secreto-123'}).get_json()
    assert d['on_behalf_of'].startswith('owner:') and 'owner-secreto-123' not in d['on_behalf_of']
    from core import identity
    assert identity.clean_declared('a\x00b\nc' + 'x' * 200) == 'a b c' + 'x' * 75
    assert identity.clean_declared('   ') is None


def test_agentes_solo_del_registro_unico_y_reloj_como_system(monkeypatch):
    from core import identity, scheduler
    from core.agents_registry import AGENT_IDS
    p = identity.agent(AGENT_IDS[0], version='2')
    assert p.id == f'agent:{AGENT_IDS[0]}@2' and p.kind == 'agent' and p.auth == 'agent_registry'
    with pytest.raises(ValueError):
        identity.agent('agente-inventado-xyz')
    seen = {}
    saved = dict(scheduler._TASKS)                 # no borrar las tareas que registró server.py (otras pruebas)
    try:
        scheduler._TASKS.clear()
        scheduler.register('ledger_seal_probe', lambda: seen.setdefault('p', identity.current()), every_s=5)
        scheduler.tick(now=10 ** 10)
    finally:
        scheduler._TASKS.clear()
        scheduler._TASKS.update(saved)
    assert seen['p'].id == 'system:ledger_seal_probe' and seen['p'].kind == 'system'
    assert identity.current() is None          # el contexto no se filtra fuera de la tarea


def test_mcp_y_legacy():
    from core import identity
    p = identity.mcp('tok_ABC', 'Claude Desktop', oauth=True)
    assert p.id == 'mcp:tok_abc' and p.kind == 'external_ai' and p.auth == 'oauth' and p.channel == 'mcp'
    lg = identity.legacy('ana')
    assert lg.id == 'legacy:ana' and lg.auth == 'none' and lg.declared_name == 'ana'


def test_mcp_ata_el_principal_a_la_peticion():
    src = _read('mcp_server/api.py')
    assert '_identity.bind_request(_identity.mcp(principal.token_id' in src


def test_cliente_manda_el_canal():
    html = _read('app.html')
    i = html.index('window._tradeFetch = async function')
    block = html[html.index('function send(url, o, pin, timeout'):i + 2000]
    assert "opts.headers['X-Khipu-Channel']" in block and "'X-Khipu-Pin-Source'" in block
    assert "Object.assign({ channel: 'terminal' }, opts || {})" in html
    voice = _read('engine/voice.js')
    assert "window._executeTradeOrder(Object.assign({ channel: 'voice' }, orderObj))" in voice
    assert "channel: o.channel === 'voice' ? 'voice' : 'ui'" in voice
    crypto = _read('engine/crypto.js')
    assert crypto.count("channel: 'crypto'") >= 2
    m = re.search(r"const CACHE = 'khipu-finance-v(\d+)'", _read('sw.js'))
    assert m and int(m.group(1)) >= 258


def test_pin_estricto_en_require_operator_es_por_produccion():
    src = _read('core/pin.py')
    assert 'strict=operator_strict()' in src and 'return in_production()' in src


# ── con base: lo que queda registrado ────────────────────────────────────────
@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': 'ID_A', 'type': 'Company'}, valid_from='2000-01-01',
                    source='test', actor='pytest', object_id='ID_A')
    yield engine
    Base.metadata.drop_all(engine)


def _onto_client():
    from flask import Flask

    from core.ledger_api import ledger_bp
    from ontology.api import ontology_bp
    app = Flask('identity_onto')
    app.config['TESTING'] = True
    app.register_blueprint(ontology_bp)
    app.register_blueprint(ledger_bp)
    return app.test_client()


@needs_db
def test_accion_con_nombre_falso_registra_el_principal(db, monkeypatch, clean):
    from sqlalchemy import select

    from core import decisions
    from ontology.db import session_scope
    from ontology.models import Event
    monkeypatch.setenv('TRADE_PIN', PIN)
    c = _onto_client()
    r = c.post('/api/ontology/actions/AnotarObjeto', headers={'X-Trade-Pin': PIN, 'X-Khipu-Channel': 'ui'},
               json={'actor': 'otra-persona-inventada', 'object_id': 'ID_A', 'texto': 'nota'})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert d['principal'] == 'op:fabrizio' and uuid.UUID(d['decision_id'])
    with session_scope() as s:
        ev = s.scalars(select(Event).where(Event.event_type == 'ActionExecuted')
                       .order_by(Event.recorded_at.desc())).first()
        assert ev.actor == 'op:fabrizio'
        assert ev.payload['declared_name'] == 'otra-persona-inventada'
        assert ev.payload['decision_id'] == d['decision_id'] and ev.payload['channel'] == 'ui'
        dec = decisions.get(s, d['decision_id'], redact=False)
    assert dec['principal_id'] == 'op:fabrizio' and dec['auth'] == 'pin' and dec['principal_kind'] == 'human'
    assert dec['declared_name'] == 'otra-persona-inventada' and dec['status'] == 'executed'
    # el Registro sigue filtrando por la etiqueta que escribió la persona
    from ontology.actions import list_actions
    with session_scope() as s:
        assert any(str(a.id) == str(ev.id) for a in list_actions(s, actor='otra-persona-inventada'))
        assert any(str(a.id) == str(ev.id) for a in list_actions(s, actor='op:fabrizio'))


@needs_db
def test_sin_pin_en_desarrollo_queda_ui_anon(db, monkeypatch, clean):
    from core import decisions
    from ontology.db import session_scope
    monkeypatch.delenv('TRADE_PIN', raising=False)
    r = _onto_client().post('/api/ontology/actions/AnotarObjeto', headers={'X-Khipu-Channel': 'voice'},
                            json={'actor': 'Fabrizio', 'object_id': 'ID_A', 'texto': 'nota'})
    assert r.status_code == 200, r.get_json()
    with session_scope() as s:
        dec = decisions.get(s, r.get_json()['decision_id'], redact=False)
    assert dec['principal_id'] == 'ui:anon' and dec['auth'] == 'none' and dec['channel'] == 'voice'


@needs_db
def test_corretaje_registra_el_principal(db, monkeypatch, clean):
    """broker_audit: actor = principal autenticado y detail._who con canal y etiqueta."""
    from flask import Flask
    from sqlalchemy import select

    from brokerage.api import _actor
    from brokerage.models import BrokerAudit
    from brokerage.service import audit
    from core import pin
    from ontology.db import session_scope
    monkeypatch.setenv('TRADE_PIN', PIN)
    app = Flask('bk_probe')
    with app.test_request_context('/x', method='POST', headers={'X-Trade-Pin': PIN, 'X-Khipu-Channel': 'crypto'}):
        assert pin.check() is None
        who = _actor({'actor': 'alguien-inventado'})
        assert who == 'op:fabrizio'
        with session_scope() as s:
            audit(s, who, 'probe_identity', detail={'x': 1})
    with session_scope() as s:
        row = s.scalars(select(BrokerAudit).where(BrokerAudit.action == 'probe_identity')).first()
        assert row.actor == 'op:fabrizio'
        assert row.detail['_who']['principal'] == 'op:fabrizio' and row.detail['_who']['channel'] == 'crypto'
        assert row.detail['_who']['auth'] == 'pin'
