"""tests/test_retention_purge.py — INFRA_OPERATIVA paso 26: purga por retención (decisión D3).

  · se purgan SOLO los cuerpos 'standard_90d' de más de 90 días que nada legal cita: ni decisiones sync (inputs,
    salida, referencias 'blob', notas en el manifiesto), ni llamadas de IA 'legal'; lo reciente y lo legal quedan;
  · la purga deja body NULL y conserva sha256/tipo/tamaño/clase/fecha + purged_at + purge_decision_id, con UNA
    decisión retention.purge (conteos, lista de sha en un blob legal); una segunda corrida es 'noop';
  · la base solo acepta esa forma exacta de UPDATE (todo lo demás: rechazado);
  · el libro sigue verificando: verify() OK tras la purga (la cadena nunca hashea cuerpos) y verify_blobs() explica
    cada cuerpo ausente — también en una base creada con la guardia de blobs ANTERIOR (emulada);
  · las claves viejas en texto plano de decision_shadow pasan a HMAC (retention.migrate), una sola vez;
  · la tarea diaria corre una vez por día UTC.
"""
import hashlib
import os
import sys
import uuid
import zlib

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')

# la guardia de blobs ANTES del paso 26 (la que tiene la base desplegada): sin purged_at/purge_decision_id ni ai_calls
OLD_BLOB_GUARD = """
CREATE OR REPLACE FUNCTION kh_blob_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'UPDATE'
     AND coalesce(current_setting('khipus.retention_job', true), '') = 'on'
     AND OLD.retention_class = 'standard_90d'
     AND OLD.created_at < now() - interval '90 days'
     AND NEW.body IS NULL AND NEW.sha256 = OLD.sha256 AND NEW.kind = OLD.kind
     AND NEW.size_bytes = OLD.size_bytes AND NEW.retention_class = OLD.retention_class
     AND NEW.created_at = OLD.created_at
     AND NOT EXISTS (SELECT 1 FROM decision_refs r JOIN decisions d ON d.id = r.decision_id
                     WHERE r.ref_kind = 'blob' AND r.ref_id = OLD.sha256 AND d.durability = 'sync')
     AND NOT EXISTS (SELECT 1 FROM decisions d
                     WHERE d.durability = 'sync' AND (d.inputs_sha = OLD.sha256 OR d.output_sha = OLD.sha256))
  THEN
    RETURN NEW;
  END IF;
  RAISE EXCEPTION 'decision_blobs es append-only: % no permitido (append-only; solo purga por retención)', TG_OP;
END $$
"""


def test_retencion_por_defecto_es_d3():
    from core import governance, retention
    governance._reset_for_tests()
    p = retention.params()
    assert p['standard_days'] == 90 and p['purge_enabled'] is True
    from core import decisions
    assert decisions.default_durability('retention.purge') == 'sync'
    assert 'retention.migrate' in decisions.KINDS


@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from core import governance
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    governance._reset_for_tests()
    assert init_schema(retries=1)
    yield engine
    governance._reset_for_tests()
    Base.metadata.drop_all(engine)


def _old_blob(engine, obj, days=100, cls='standard_90d', kind='inputs'):
    """Un blob con fecha vieja (INSERT con created_at explícito: solo crece)."""
    from sqlalchemy import text

    from core.decisions import canonical
    b = canonical(obj)
    sha = hashlib.sha256(b).hexdigest()
    with engine.begin() as c:
        c.execute(text("INSERT INTO decision_blobs (sha256, kind, body, size_bytes, retention_class, created_at) "
                       "VALUES (:s, :k, :b, :n, :c, now() - make_interval(days => :d)) ON CONFLICT DO NOTHING"),
                  {'s': sha, 'k': kind, 'b': zlib.compress(b, 6), 'n': len(b), 'c': cls, 'd': days})
    return sha


def _blob_row(engine, sha):
    from sqlalchemy import text
    with engine.connect() as c:
        return c.execute(text('SELECT sha256, kind, body, size_bytes, retention_class, created_at, purged_at, '
                              'purge_decision_id FROM decision_blobs WHERE sha256 = :s'), {'s': sha}).first()


@pytest.fixture(scope='module')
def scene(db):
    """Blobs viejos con distintos destinos + decisiones/llamadas de IA que los citan."""
    from sqlalchemy import text

    from core import decisions, identity
    from ontology.db import session_scope
    p = identity.system('pytest_retention')
    sc = {}
    sc['async_old'] = _old_blob(db, {'q': 'qué pasa si cae TSMC', 'n': 1})          # chat/qué-pasaría-si → SÍ
    with db.begin() as c:                      # lo citó una llamada de IA de 90 días HACE 100 días: nada reciente
        c.execute(text("INSERT INTO ai_calls (id, started_at, tier, prompt_sha, system_sha, input_blob, "
                       "retention_class, ok) VALUES (CAST(:i AS uuid), now() - interval '100 days', 'fast', :p, :p, "
                       ":s, 'standard_90d', true)"), {'i': str(uuid.uuid4()), 'p': '2' * 64, 's': sc['async_old']})
    # revisión batch G: el MISMO contenido visto por primera vez hace 100 días y citado HOY por un qué-pasaría-si
    # (la fila del blob guarda su PRIMERA aparición) → NO: lo de los últimos 90 días se conserva (D3)
    sc['async_recent'] = _old_blob(db, {'q': 'qué pasa si cae TSMC', 'n': 3})
    with decisions.decision_scope('whatif.shock', p, session=None) as ctx:
        ctx.inputs_sha = ctx.blob('inputs', {'q': 'qué pasa si cae TSMC', 'n': 3})
        ctx.output = {'ok': 1}
    decisions.flush_async()
    sc['orphan_old'] = _old_blob(db, {'huerfano': True})                             # nadie lo cita → SÍ
    sc['sync_inputs'] = _old_blob(db, {'q': 'acción de ontología', 'n': 2})          # inputs de una sync → NO
    sc['sync_note'] = _old_blob(db, {'note': 'nota del operador'}, kind='payload')  # nota en el manifiesto → NO
    sc['sync_ref'] = _old_blob(db, {'evidencia': 'E1'}, kind='payload')             # ref 'blob' de una sync → NO
    with session_scope() as s:
        with decisions.decision_scope('alert.rule', identity.operator(), session=s, subject={'x': 1}) as ctx:
            ctx.inputs_sha = ctx.blob('inputs', {'q': 'acción de ontología', 'n': 2})
            ctx.extra['note_blob'] = ctx.blob('payload', {'note': 'nota del operador'})
            ctx.evidence('blob', sc['sync_ref'])
            ctx.output = {'ok': 2}
    sc['ai_legal'] = _old_blob(db, {'system': 'eres el comité'}, kind='ai_system')   # system de una IA 'legal' → NO
    with db.begin() as c:
        c.execute(text("INSERT INTO ai_calls (id, started_at, tier, prompt_sha, system_sha, system_blob, "
                       "retention_class, ok) VALUES (CAST(:i AS uuid), now(), 'deep', :p, :p, :s, 'legal', true)"),
                  {'i': str(uuid.uuid4()), 'p': '1' * 64, 's': sc['ai_legal']})
    sc['recent'] = _old_blob(db, {'reciente': True}, days=10)                       # < 90 días → NO
    sc['legal_old'] = _old_blob(db, {'legal': True}, cls='legal')                   # legal → NUNCA
    return sc


def _cols_ai_calls(engine):
    from sqlalchemy import text
    with engine.connect() as c:
        return {r[0] for r in c.execute(text("SELECT column_name FROM information_schema.columns "
                                             "WHERE table_name = 'ai_calls'")).all()}


@needs_db
def test_purga_solo_lo_vencido_y_sin_cita_legal(db, scene):
    from sqlalchemy import text

    from core import ledger, retention
    ledger.seal(db)
    v0 = ledger.verify(engine=db)
    assert v0['ok'], v0['broken']
    dry = retention.purge(dry_run=True)
    assert dry['dry_run'] and dry['purged'] == 0
    out = retention.purge()
    gone = {k for k, sha in scene.items() if _blob_row(db, sha).body is None}
    assert gone == {'async_old', 'orphan_old'}, (gone, out)
    assert out['purged'] == 2 and out['protected_by_manifest'] >= 0 and out['decision_id']
    for k in ('async_old', 'orphan_old'):
        r = _blob_row(db, scene[k])
        assert r.sha256 == scene[k] and r.size_bytes > 0 and r.retention_class == 'standard_90d'
        assert r.purged_at is not None and str(r.purge_decision_id) == out['decision_id']
    with db.connect() as c:
        d = c.execute(text('SELECT kind, durability, status, output, principal_id FROM decisions '
                           'WHERE id = CAST(:i AS uuid)'), {'i': out['decision_id']}).first()
    assert (d.kind, d.durability, d.status) == ('retention.purge', 'sync', 'executed')
    assert d.principal_id == 'system:retention_purge' and d.output['purged'] == 2
    assert d.output['by_kind'] == {'inputs': 2}
    # el libro sigue verificando: la cadena no hashea cuerpos; los blobs se explican por su sha
    ledger.seal(db)
    v1 = ledger.verify(engine=db)
    assert v1['ok'], v1['broken']
    vb = ledger.verify_blobs(db)
    assert vb['ok'] and vb['purged'] == 2 and vb['present'] >= 6, vb
    # segunda corrida: nada más que purgar → 'noop'
    out2 = retention.purge()
    assert out2['purged'] == 0
    with db.connect() as c:
        assert c.execute(text('SELECT status FROM decisions WHERE id = CAST(:i AS uuid)'),
                         {'i': out2['decision_id']}).scalar() == 'noop'


@needs_db
def test_la_base_solo_acepta_la_forma_exacta_de_la_purga(db, scene):
    from sqlalchemy import text
    did = str(uuid.uuid4())

    def upd(sql, params, job=True):
        with db.begin() as c:
            if job:
                c.execute(text("SELECT set_config('khipus.retention_job', 'on', true)"))
            c.execute(text(sql), params)
    purge_sql = ('UPDATE decision_blobs SET body = NULL, purged_at = now(), purge_decision_id = CAST(:d AS uuid) '
                 'WHERE sha256 = :s')
    for key in ('legal_old', 'recent', 'sync_inputs', 'sync_ref', 'ai_legal', 'async_recent'):   # sync_note: el job
        with pytest.raises(Exception):
            upd(purge_sql, {'d': did, 's': scene[key]})
    with pytest.raises(Exception):                         # devolver un cuerpo purgado: nunca
        upd('UPDATE decision_blobs SET body = :b WHERE sha256 = :s', {'b': b'x', 's': scene['async_old']})
    with pytest.raises(Exception):                         # cambiar el cuerpo (no NULL): nunca
        upd('UPDATE decision_blobs SET body = :b WHERE sha256 = :s', {'b': b'x', 's': scene['recent']})
    with pytest.raises(Exception):                         # re-purgar (ya sin cuerpo): no
        upd(purge_sql, {'d': did, 's': scene['async_old']})
    with pytest.raises(Exception):
        with db.begin() as c:
            c.execute(text('DELETE FROM decision_blobs WHERE sha256 = :s'), {'s': scene['orphan_old']})
    with pytest.raises(Exception):
        with db.begin() as c:
            c.execute(text('TRUNCATE decision_blobs CASCADE'))


@needs_db
def test_claves_viejas_de_la_sombra_pasan_a_hmac(db):
    from sqlalchemy import text

    from core import retention
    with db.begin() as c:
        for k in ('¿cuánto vale nvidia hoy?', 'hmac:' + 'a' * 40, 'len:12', '', 'compra 10 AAPL'):
            c.execute(text("INSERT INTO decision_shadow (at, feature, key, decision, actual) "
                           "VALUES (now(), 'chat_gate', :k, '{}'::jsonb, '{}'::jsonb)"), {'k': k})
    out = retention.migrate_shadow_keys()
    assert out['migrated'] == 2 and out['decision_id']
    with db.connect() as c:
        keys = [r[0] for r in c.execute(text('SELECT key FROM decision_shadow ORDER BY id')).all()]
        d = c.execute(text("SELECT kind, status, output FROM decisions WHERE id = CAST(:i AS uuid)"),
                      {'i': out['decision_id']}).first()
    assert not any('nvidia' in k or 'AAPL' in k for k in keys)
    assert sum(1 for k in keys if k.startswith('hmac0:')) == 2 and 'len:12' in keys and '' in keys
    assert (d.kind, d.status, d.output['migrated']) == ('retention.migrate', 'executed', 2)
    assert retention.migrate_shadow_keys() == {'migrated': 0}          # idempotente


@needs_db
def test_tarea_diaria_una_vez_por_dia(db):
    from core import retention
    first = retention.daily_job(force=True)
    assert 'purge' in first
    assert retention.daily_job() == {'skipped': 'already_today'}
    st = retention.status()
    assert st['last'] and st['pending'] is not None


@needs_db
def test_base_con_la_guardia_de_blobs_anterior(db):
    """Base creada por el código desplegado (guardia de blobs vieja): el arranque instala la nueva sin tocar datos;
    una purga con la forma nueva pasa, el libro verifica antes y después."""
    from sqlalchemy import text

    from core import ledger, ledger_ddl, retention
    with db.begin() as c:
        c.execute(text(OLD_BLOB_GUARD))
        src = c.execute(text("SELECT prosrc FROM pg_proc WHERE proname = 'kh_blob_guard'")).scalar()
    assert 'purge_decision_id' not in src
    sha = _old_blob(db, {'legado': 'chat viejo'})
    ledger.seal(db)
    assert ledger.verify(engine=db)['ok']
    assert ledger_ddl.ensure_all(db)                       # = arranque del código nuevo sobre esa base
    with db.connect() as c:
        src = c.execute(text("SELECT prosrc FROM pg_proc WHERE proname = 'kh_blob_guard'")).scalar()
    assert 'purge_decision_id' in src and 'ai_calls' in src
    out = retention.purge()
    assert out['purged'] >= 1 and _blob_row(db, sha).body is None
    ledger.seal(db)
    v = ledger.verify(engine=db)
    assert v['ok'], v['broken']
    assert ledger.verify_blobs(db)['ok']
