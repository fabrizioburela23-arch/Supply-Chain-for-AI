"""tests/test_ledger_anchor.py — INFRA_OPERATIVA paso 7: ancla diaria, linaje y cadena rota que bloquea el dinero real.

Garantiza (docs/INFRA_OPERATIVA.md §2.8, §7 y decisión D7):
  · `anchor()` escribe UNA fila por día y linaje en `ledger_anchors` (idempotente) con la cabeza de la cadena y el
    resultado de la verificación; `ledger_anchors` es append-only;
  · GET /api/ledger/anchor es PÚBLICO y devuelve SOLO {available, day, head_seal, head_hash};
  · una verificación con sellos rotos deja `ledger.chain_break` y el DINERO REAL queda bloqueado (brokerage:
    control `ledger_chain` en preview y confirm; cuenta de la casa: 423) — el PAPEL no se toca;
  · `POST /api/ledger/chain_ack` con PIN (persona) deja `ledger.chain_ack` y el dinero real vuelve; la misma
    ruptura no se vuelve a registrar; una NUEVA sí;
  · linaje: cluster distinto o contador de transacciones por detrás → `ledger.lineage_break` + linaje nuevo;
  · scripts/fetch_ledger_anchor.py valida la forma y el workflow smoke-mcp.yml guarda el ancla como artefacto.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


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
        for oid in ('AN_A', 'AN_B'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=oid)
    from core import ledger
    ledger._invalidate_chain()
    yield engine
    ledger._invalidate_chain()
    Base.metadata.drop_all(engine)


def _seal(engine):
    import time

    from core import ledger
    for _ in range(80):
        ledger.seal()
        if ledger.verify()['checked'] and not _pending(engine):
            return
        time.sleep(0.25)


def _pending(engine):
    from sqlalchemy import text
    with engine.connect() as c:
        return c.execute(text("SELECT count(*) FROM events t WHERE NOT EXISTS (SELECT 1 FROM ledger_seals s "
                              "WHERE s.row_table = 'events' AND s.row_id = t.id::text)")).scalar()


@pytest.fixture()
def app_client(monkeypatch):
    monkeypatch.setenv('TRADE_PIN', 'pin-anchor-1234')
    import server
    from core import pin
    pin._reset_for_tests()
    server.app.config['TESTING'] = True
    return server.app.test_client()


# ── ancla ────────────────────────────────────────────────────────────────────
@needs_db
def test_ancla_diaria_una_por_dia_y_append_only(db):
    from sqlalchemy import text

    from core import ledger
    _seal(db)
    a1 = ledger.anchor()
    assert a1['created'] is True and a1['verify']['ok'] is True
    head = ledger.verify()['head']
    assert a1['anchor']['head_seal'] == head['seal_no'] and a1['anchor']['head_hash'] == head['hash']
    assert len(a1['anchor']['head_hash']) == 64 and a1['anchor']['verified'] is True
    a2 = ledger.anchor()
    assert a2['created'] is False and a2['anchor']['day'] == a1['anchor']['day']
    with db.connect() as c:
        assert c.execute(text('SELECT count(*) FROM ledger_anchors')).scalar() == 1
    for sql in ('UPDATE ledger_anchors SET head_seal = 0', 'DELETE FROM ledger_anchors',
                'TRUNCATE ledger_anchors'):
        with pytest.raises(Exception) as ei:
            with db.begin() as c:
                c.execute(text(sql))
        assert 'append-only' in str(ei.value)


@needs_db
def test_anchor_publico_solo_cabeza(db, app_client):
    from core import ledger
    ledger.anchor()
    r = app_client.get('/api/ledger/anchor')
    assert r.status_code == 200
    d = r.get_json()
    assert set(d) == {'available', 'day', 'head_seal', 'head_hash'}
    assert len(d['head_hash']) == 64 and isinstance(d['head_seal'], int)
    from scripts.fetch_ledger_anchor import validate
    assert validate(d) == []
    st = app_client.get('/api/ledger/status').get_json()
    assert st['chain']['broken'] is False and st['chain']['anchor']['day'] == d['day']


# ── cadena rota → dinero real bloqueado hasta el ack ─────────────────────────
def _tamper(engine, oid='AN_A'):
    """Cambia una fila ya sellada desactivando el disparador (lo que haría un superusuario)."""
    from sqlalchemy import text
    with engine.begin() as c:
        c.execute(text('ALTER TABLE events DISABLE TRIGGER events_no_modify'))
        c.execute(text("UPDATE events SET actor = 'hacker' WHERE object_id = :o"), {'o': oid})
        c.execute(text('ALTER TABLE events ENABLE TRIGGER events_no_modify'))


@needs_db
def test_cadena_rota_bloquea_dinero_real_hasta_ack(db, app_client, monkeypatch):
    from sqlalchemy import text

    from brokerage import risk
    from core import ledger
    _seal(db)
    assert ledger.money_gate()[0] is True
    _tamper(db, 'AN_A')
    v = ledger.verify(record_break=True)
    assert not v['ok'] and v.get('break_id')
    st = ledger.chain_state(fresh=True)
    assert st['broken'] and st['break_id'] == v['break_id']
    ok, es, en = ledger.money_gate()
    assert ok is False and 'CADENA' in es and 'CHAIN' in en

    # brokerage: el control ledger_chain bloquea SOLO dinero real
    monkeypatch.setenv('BROKERAGE_LIVE_ENABLED', 'on')
    base = {'client': {'status': 'active', 'mode': 'live', 'live_enabled': True, 'connected': True,
                       'risk_profile': 'moderado'},
            'order': {'symbol': 'NVDA', 'side': 'buy', 'notional': 100.0, 'order_type': 'market'},
            'account': {'equity': 100000, 'cash': 50000, 'buying_power': 50000}, 'positions': [],
            'price': 100.0, 'ref_price': 100.0, 'est_usd': 100.0, 'daily_used_usd': 0, 'market_open': True,
            'clock_source': 'alpaca'}
    live = {c['name']: c for c in risk.run_checks(base)}
    assert live['ledger_chain']['ok'] is False and risk.is_blocked(list(live.values()))
    assert live['ledger_chain']['detail_en']
    paper = {c['name']: c for c in risk.run_checks({**base, 'client': {**base['client'], 'mode': 'paper'}})}
    assert 'ledger_chain' not in paper and not risk.is_blocked(list(paper.values()))

    # cuenta de la casa en dinero real → 423; en papel no aplica
    import server
    monkeypatch.setattr(server, 'ALPACA_BASE', 'https://api.alpaca.markets')
    with server.app.test_request_context():
        resp = server._house_ledger_block()
        assert resp is not None and resp[1] == 423 and resp[0].get_json()['code'] == 'ledger_chain_broken'
    monkeypatch.setattr(server, 'ALPACA_BASE', 'https://paper-api.alpaca.markets')
    with server.app.test_request_context():
        assert server._house_ledger_block() is None

    # el ack exige PIN (y una persona)
    r = app_client.post('/api/ledger/chain_ack', json={'note': 'revisado'})
    assert r.status_code == 401
    r = app_client.post('/api/ledger/chain_ack', json={'note': 'revisado: prueba de manipulación'},
                        headers={'X-Trade-Pin': 'pin-anchor-1234'})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert d['break_id'] == v['break_id']
    assert ledger.money_gate()[0] is True
    assert app_client.get('/api/ledger/chain').get_json()['real_money_allowed'] is True
    with db.connect() as c:
        row = c.execute(text("SELECT principal_id, auth, status, parent_id::text FROM decisions "
                             "WHERE kind = 'ledger.chain_ack'")).first()
    assert row.principal_id == 'op:fabrizio' and row.auth == 'pin' and row.status == 'approved'
    assert row.parent_id == v['break_id']
    r = app_client.post('/api/ledger/chain_ack', json={}, headers={'X-Trade-Pin': 'pin-anchor-1234'})
    assert r.status_code == 404 and r.get_json()['code'] == 'nothing_to_ack'

    # la MISMA ruptura no se vuelve a registrar (ni a bloquear); una nueva sí
    v2 = ledger.verify(record_break=True)
    assert not v2['ok'] and ledger.money_gate()[0] is True
    with db.connect() as c:
        assert c.execute(text("SELECT count(*) FROM decisions WHERE kind = 'ledger.chain_break'")).scalar() == 1
    _tamper(db, 'AN_B')
    v3 = ledger.verify(record_break=True)
    assert v3['break_id'] and v3['break_id'] != v['break_id']
    assert ledger.money_gate()[0] is False
    r = app_client.post('/api/ledger/chain_ack', json={'note': 'segunda'}, headers={'X-Trade-Pin': 'pin-anchor-1234'})
    assert r.status_code == 200 and ledger.money_gate()[0] is True


def test_money_gate_sin_base_solo_papel(monkeypatch):
    import ontology.db as odb

    from core import ledger
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    ok, es, en = ledger.money_gate()
    assert ok is False and 'PAPEL' in es and 'PAPER' in en


def test_money_gate_falla_cerrado_si_no_puede_leer(monkeypatch):
    import ontology.db as odb

    from core import ledger
    monkeypatch.setattr(odb, 'ontology_available', lambda: True)

    def boom(**k):
        raise RuntimeError('db caída')
    monkeypatch.setattr(ledger, 'chain_state', boom)
    ok, es, en = ledger.money_gate()
    assert ok is False and 'falla cerrado' in es and 'fail closed' in en


# ── linaje ───────────────────────────────────────────────────────────────────
@needs_db
def test_linaje_txid_por_detras_abre_linaje_nuevo(db):
    from sqlalchemy import text

    from core import ledger
    old = ledger.lineage_id()
    assert ledger.check_lineage()['ok'] is True
    # simula una base restaurada: una decisión escrita con un txid MAYOR que el contador actual
    with db.begin() as c:
        c.execute(text(
            "INSERT INTO decisions (id, kind, durability, status, principal_id, principal_kind, auth, channel, "
            "valid_at, txid, lineage_id, release_hash, code_sha, manifest, manifest_sha) VALUES "
            "(gen_random_uuid(), 'audit.replay', 'sync', 'recorded', 'system:test', 'system', 'scheduler', "
            "'scheduler', now(), '999999999999'::xid8, :l, :r, 'test', '{}'::jsonb, :r)"),
            {'l': old, 'r': '0' * 64})
    out = ledger.check_lineage()
    assert out['ok'] is False and out['reason'] == 'txid_behind'
    assert ledger.lineage_id() != old and str(ledger.lineage_id()) == out['lineage_id']
    with db.connect() as c:
        row = c.execute(text("SELECT output FROM decisions WHERE kind = 'ledger.lineage_break'")).first()
    assert row.output['old_lineage'] == str(old) and row.output['reason'] == 'txid_behind'
    assert ledger.check_lineage()['ok'] is True          # idempotente: el linaje nuevo no cumple la condición


@needs_db
def test_linaje_cluster_distinto(db):
    from sqlalchemy import text

    from core import ledger
    cur = ledger.lineage_id()
    with db.begin() as c:
        real = c.execute(text('SELECT system_identifier FROM pg_control_system()')).scalar()
        if not real:
            pytest.skip('sin permiso para pg_control_system')
        c.execute(text("INSERT INTO ledger_meta (lineage_id, cluster_id, first_txid, note) VALUES "
                       "(gen_random_uuid(), 12345, pg_current_xact_id(), 'otro cluster (prueba)')"))
    out = ledger.check_lineage()
    assert out['ok'] is False and out['reason'] == 'cluster_changed' and out['cluster_now'] == str(real)
    assert ledger.lineage_id() != cur
    assert ledger.check_lineage()['ok'] is True


# ── workflow y script ────────────────────────────────────────────────────────
def test_fetch_ledger_anchor_valida_forma():
    from scripts.fetch_ledger_anchor import validate
    good = {'available': True, 'day': '2026-10-13', 'head_seal': 42, 'head_hash': 'a' * 64}
    assert validate(good) == []
    assert validate({**good, 'head_hash': 'xyz'})
    assert validate({**good, 'manifest': {}})                  # una respuesta pública nunca trae contenido
    assert validate({**good, 'head_seal': -1})


def test_fetch_ledger_anchor_main(tmp_path, monkeypatch):
    import scripts.fetch_ledger_anchor as f
    monkeypatch.setattr(f, 'fetch', lambda url, retries=4: (200, {'available': True, 'day': '2026-10-13',
                                                                   'head_seal': 7, 'head_hash': 'b' * 64}))
    out, summ, gho = tmp_path / 'a.json', tmp_path / 's.md', tmp_path / 'o.txt'
    monkeypatch.setenv('GITHUB_OUTPUT', str(gho))
    assert f.main(['--url', 'https://x.example', '--out', str(out), '--summary', str(summ)]) == 0
    rec = json.loads(out.read_text())
    assert rec['head_seal'] == 7 and rec['source'] == 'https://x.example/api/ledger/anchor'
    assert 'day=2026-10-13' in gho.read_text() and 'b' * 64 in summ.read_text()
    monkeypatch.setattr(f, 'fetch', lambda url, retries=4: (503, None))
    assert f.main(['--out', str(tmp_path / 'b.json')]) == 0           # sin ancla: aviso, no rojo
    monkeypatch.setattr(f, 'fetch', lambda url, retries=4: (200, {'day': 'hoy', 'head_seal': 1, 'head_hash': 'z'}))
    assert f.main(['--out', str(tmp_path / 'c.json')]) == 1


def test_workflow_guarda_el_ancla():
    with open(os.path.join(ROOT, '.github', 'workflows', 'smoke-mcp.yml'), encoding='utf-8') as fh:
        y = fh.read()
    assert 'schedule:' in y and 'cron:' in y
    assert 'scripts/fetch_ledger_anchor.py' in y and 'actions/upload-artifact@v4' in y
    assert 'GITHUB_STEP_SUMMARY' in y
