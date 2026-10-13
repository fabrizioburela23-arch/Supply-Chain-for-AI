"""tests/test_ledger_guard.py — INFRA_OPERATIVA paso 22: guardia de proyecciones «sin decisión no hay cambio».

  · la guardia cubre las 7 tablas que proyectan decisiones con sus nombres REALES (modelos) y broker_orders también en
    INSERT;
  · modo AVISO (policy.guard@1.0.0, el vigente): la escritura sin decisión SIGUE, se cuenta UNA vez por
    (transacción, tabla, operación) en kh_guard_violations y el camino del código queda en memoria (🩺);
  · con decisión (decision_scope sync) no cuenta nada y no cuesta (medido);
  · modo BLOQUEO solo con policy.guard@2.0.0 activado con PIN (governance.activate → kh_guard_modes, append-only);
    las variables de entorno no lo cambian (D2); deshacer = volver a 1.0.0;
  · una base creada por el código ANTERIOR (sin guardia y con la guardia de blobs vieja) la recibe en el arranque.
"""
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


def test_tablas_vigiladas_son_las_reales():
    from core import ledger_guard
    from ontology.db import init_schema  # noqa: F401 — registra los modelos opcionales
    import brokerage.models  # noqa: F401
    import research.models  # noqa: F401
    from ontology.models import Base
    names = set(Base.metadata.tables)
    assert set(ledger_guard.GUARD_TABLES) <= names
    assert ledger_guard.GUARD_TABLES['broker_orders'] == ('INSERT', 'UPDATE', 'DELETE')
    assert all('UPDATE' in ops and 'DELETE' in ops for ops in ledger_guard.GUARD_TABLES.values())
    from core import ledger_ddl
    assert {'kh_guard_violations', 'kh_guard_modes'} <= set(ledger_ddl.APPEND_ONLY_TABLES)


def test_artefactos_de_la_guardia():
    from core import governance
    governance._reset_for_tests()
    assert governance.repo_bundle().artifacts['policy.guard']['semver'] == '1.0.0'     # el release del repo: AVISO
    v2 = governance.available_artifact('policy.guard', '2.0.0')
    assert v2['params']['mode'] == 'enforce' and v2['activation'] == 'pin' and v2['change_kind'] == 'major'


def test_variable_de_entorno_no_cambia_el_modo(monkeypatch):
    from core import governance, ledger_guard
    governance._reset_for_tests()
    monkeypatch.setenv('KHIPU_GUARD_MODE', 'enforce')
    monkeypatch.setenv('GUARD_MODE', 'enforce')
    assert ledger_guard.policy_mode() == 'warn'


# ── con base ─────────────────────────────────────────────────────────────────
@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from core import governance, ledger_guard
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    governance._reset_for_tests()
    ledger_guard._reset_for_tests()
    assert init_schema(retries=1)
    yield engine
    governance._reset_for_tests()
    Base.metadata.drop_all(engine)


def _alert(engine, rid='g-al-1'):
    import uuid

    from sqlalchemy import text
    rid = str(uuid.uuid5(uuid.NAMESPACE_URL, rid))
    with engine.begin() as c:            # INSERT en alerts no está vigilado (solo UPDATE/DELETE)
        c.execute(text("INSERT INTO alerts (id, owner, rule, channel, is_active) VALUES "
                       "(CAST(:i AS uuid), 'pytest', '{}'::jsonb, 'browser', true) ON CONFLICT DO NOTHING"), {'i': rid})
    return rid


def _viol_rows(engine, since_id=0):
    from sqlalchemy import text
    with engine.connect() as c:
        return c.execute(text('SELECT id, table_name, op, mode FROM kh_guard_violations WHERE id > :i ORDER BY id'),
                         {'i': since_id}).all()


def _max_viol(engine):
    from sqlalchemy import text
    with engine.connect() as c:
        return c.execute(text('SELECT coalesce(max(id), 0) FROM kh_guard_violations')).scalar()


@needs_db
def test_disparadores_en_las_siete_tablas(db):
    from core import ledger_guard
    with db.connect() as c:
        tp = ledger_guard.triggers_present(c)
        assert all(tp.values()), tp
        from sqlalchemy import text
        assert c.execute(text('SELECT mode FROM kh_guard_modes ORDER BY id DESC LIMIT 1')).scalar() == 'warn'


@needs_db
def test_aviso_cuenta_una_vez_por_transaccion_y_anota_el_camino(db):
    from sqlalchemy import text

    from core import ledger_guard
    rid = _alert(db)
    m0 = _max_viol(db)
    ledger_guard._reset_for_tests()
    with db.begin() as c:                               # SIN decisión: sigue (modo aviso)
        c.execute(text('UPDATE alerts SET is_active = false WHERE id = CAST(:i AS uuid)'), {'i': rid})
        c.execute(text('UPDATE alerts SET is_active = true WHERE id = CAST(:i AS uuid)'), {'i': rid})     # misma transacción
    rows = _viol_rows(db, m0)
    assert [(r.table_name, r.op, r.mode) for r in rows] == [('alerts', 'UPDATE', 'warn')]
    with db.connect() as c:
        assert c.execute(text('SELECT is_active FROM alerts WHERE id = CAST(:i AS uuid)'), {'i': rid}).scalar() is True
    st = ledger_guard.status(fresh=True)
    assert st['mode'] == 'warn' and st['total'] >= 1
    assert any(p['table'] == 'alerts' and 'tests/test_ledger_guard.py' in p['path'] for p in st['paths']), st['paths']
    with db.begin() as c:                               # otra transacción → otra fila
        c.execute(text('UPDATE alerts SET is_active = false WHERE id = CAST(:i AS uuid)'), {'i': rid})
    assert len(_viol_rows(db, m0)) == 2
    with db.begin() as c:                               # sin cambio real (mismo valor) no hay nada que decidir
        c.execute(text('UPDATE alerts SET is_active = false WHERE id = CAST(:i AS uuid)'), {'i': rid})
    assert len(_viol_rows(db, m0)) == 2


@needs_db
def test_con_decision_no_cuenta(db):
    from sqlalchemy import text

    from core import decisions, identity
    from ontology.db import session_scope
    rid = _alert(db, 'g-al-2')
    m0 = _max_viol(db)
    with session_scope() as s:
        with decisions.decision_scope('alert.rule', identity.operator(), session=s, subject={'alert_id': rid}) as ctx:
            s.execute(text('UPDATE alerts SET is_active = false WHERE id = CAST(:i AS uuid)'), {'i': rid})
            ctx.output = {'active': False}
    assert _viol_rows(db, m0) == []


@needs_db
def test_decision_registrada_despues_en_la_misma_transaccion_cuenta(db):
    """Confirmar una orden o aprobar una propuesta escribe la fila y DESPUÉS registra la decisión, en la misma
    transacción: la guardia mira al CONFIRMAR (txid de la decisión), no en el instante de la escritura."""
    from sqlalchemy import text

    from core import decisions, identity
    from ontology.db import session_scope
    rid = _alert(db, 'g-al-7')
    m0 = _max_viol(db)
    with session_scope() as s:
        s.execute(text('UPDATE alerts SET is_active = false WHERE id = CAST(:i AS uuid)'), {'i': rid})
        ctx = decisions.DecisionCtx('alert.rule', identity.operator(), subject={'alert_id': rid})
        ctx.output = {'active': False}
        decisions.record(s, ctx, status='executed')       # sin decision_scope: sin GUC, solo la fila del libro
    assert _viol_rows(db, m0) == []
    with pytest.raises(Exception):                         # en BLOQUEO, la misma escritura SIN decisión no confirma
        with session_scope() as s:
            s.execute(text("SELECT set_config('khipus.guard_mode', 'enforce', true)"))
            s.execute(text('UPDATE alerts SET is_active = true WHERE id = CAST(:i AS uuid)'), {'i': rid})
    with db.connect() as c:
        assert c.execute(text('SELECT is_active FROM alerts WHERE id = CAST(:i AS uuid)'), {'i': rid}).scalar() is False


@needs_db
def test_columnas_de_observacion_no_cuentan(db):
    """Leer la cuenta de Alpaca actualiza el máximo histórico y el último patrimonio: es el mundo observado, no una
    decisión. Cambiar el perfil de riesgo de un cliente SÍ lo es."""
    from sqlalchemy import text
    with db.begin() as c:
        c.execute(text("INSERT INTO broker_clients (id, name, mode, live_enabled, auth_type, risk_profile, risk_limits, "
                       "mandate, status) VALUES ('g-cli-1', 'Cliente', 'paper', false, 'keys', 'moderado', '{}', '{}', "
                       "'active') ON CONFLICT DO NOTHING"))
    m0 = _max_viol(db)
    with db.begin() as c:
        c.execute(text("UPDATE broker_clients SET hwm_equity = 1000, hwm_at = now(), last_equity = 990, "
                       "last_snapshot_at = now(), updated_at = now() WHERE id = 'g-cli-1'"))
    assert _viol_rows(db, m0) == []
    with db.begin() as c:
        c.execute(text("UPDATE broker_clients SET risk_profile = 'agresivo', hwm_equity = 1100 WHERE id = 'g-cli-1'"))
    assert [(r.table_name, r.op) for r in _viol_rows(db, m0)] == [('broker_clients', 'UPDATE')]


@needs_db
def test_insert_en_broker_orders_sin_decision_cuenta(db):
    from sqlalchemy import text
    m0 = _max_viol(db)
    with db.begin() as c:
        cols = {r[0] for r in c.execute(text("SELECT column_name FROM information_schema.columns "
                                             "WHERE table_name = 'broker_orders'")).all()}
        assert 'id' in cols
    # sin decisión y sin las columnas obligatorias, el INSERT falla por NOT NULL antes o después del disparador; lo
    # que importa es que el disparador EXISTE para INSERT
    with db.connect() as c:
        for tg in ('broker_orders_kh_guard', 'broker_orders_kh_guard_commit'):
            ev = c.execute(text("SELECT pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class r ON r.oid = t.tgrelid "
                                "WHERE r.relname = 'broker_orders' AND t.tgname = :g"), {'g': tg}).scalar()
            assert 'INSERT' in ev and 'UPDATE' in ev and 'DELETE' in ev
        assert 'DEFERRABLE INITIALLY DEFERRED' in ev
    assert _viol_rows(db, m0) == []


@needs_db
def test_modo_bloqueo_por_guc_de_prueba(db):
    from sqlalchemy import text

    from core import decisions, identity
    from ontology.db import session_scope
    rid = _alert(db, 'g-al-3')
    with pytest.raises(Exception) as ei:
        with db.begin() as c:
            c.execute(text("SELECT set_config('khipus.guard_mode', 'enforce', true)"))
            c.execute(text('UPDATE alerts SET is_active = false WHERE id = CAST(:i AS uuid)'), {'i': rid})
    assert 'sin decision registrada' in str(ei.value) and 'without a recorded decision' in str(ei.value)
    with session_scope() as s:                          # con decisión pasa aunque el modo sea bloqueo
        s.execute(text("SELECT set_config('khipus.guard_mode', 'enforce', true)"))
        with decisions.decision_scope('alert.rule', identity.operator(), session=s, subject={'alert_id': rid}):
            s.execute(text('UPDATE alerts SET is_active = false WHERE id = CAST(:i AS uuid)'), {'i': rid})


@needs_db
def test_bloqueo_solo_con_policy_guard_2_activado_con_pin(db):
    from sqlalchemy import text

    from core import governance, identity, ledger_guard
    from ontology.db import session_scope
    rid = _alert(db, 'g-al-4')
    governance.refresh()
    from core import governance_flow
    with pytest.raises(governance.GovernanceConflict) as ei:          # revisión batch G: MAYOR sin regresión → no
        with session_scope() as s:
            governance.activate(s, identity.operator(), {'policy.guard': '2.0.0'})
    assert ei.value.code == 'regression_required'
    governance_flow.validate(identity.operator(), 'policy.guard', '2.0.0')
    with session_scope() as s:
        out = governance.activate(s, identity.operator(), {'policy.guard': '2.0.0'}, note='prueba paso 22')
    assert out['four_eyes'] == 'unavailable'           # MAJOR, D1: un solo aprobador
    governance.refresh()
    assert ledger_guard.policy_mode() == 'enforce'
    with db.connect() as c:
        last = c.execute(text('SELECT mode, artifact FROM kh_guard_modes ORDER BY id DESC LIMIT 1')).first()
    assert last.mode == 'enforce' and last.artifact == 'policy.guard@2.0.0'
    with pytest.raises(Exception):
        with db.begin() as c:
            c.execute(text('UPDATE alerts SET is_active = false WHERE id = CAST(:i AS uuid)'), {'i': rid})
    with session_scope() as s:                          # deshacer = volver a 1.0.0 (otra decisión, con PIN)
        governance.activate(s, identity.operator(), {'policy.guard': '1.0.0'})
    governance.refresh()
    with db.begin() as c:
        c.execute(text('UPDATE alerts SET is_active = false WHERE id = CAST(:i AS uuid)'), {'i': rid})     # aviso otra vez
    with db.connect() as c:
        modes = [r[0] for r in c.execute(text('SELECT mode FROM kh_guard_modes ORDER BY id')).all()]
    assert modes[-3:] == ['warn', 'enforce', 'warn'] or modes[-2:] == ['enforce', 'warn']


@needs_db
def test_tablas_de_la_guardia_son_append_only(db):
    from sqlalchemy import text
    rid = _alert(db, 'g-al-5')
    with db.begin() as c:
        c.execute(text('UPDATE alerts SET is_active = true WHERE id = CAST(:i AS uuid)'), {'i': rid})
    for sql in ('UPDATE kh_guard_violations SET mode = mode', 'DELETE FROM kh_guard_violations',
                "UPDATE kh_guard_modes SET mode = 'warn'", 'DELETE FROM kh_guard_modes'):
        with pytest.raises(Exception):
            with db.begin() as c:
                c.execute(text(sql))


@needs_db
def test_costo_de_la_guardia_con_decision(db):
    """Con decisión la guardia es UNA lectura de GUC por fila: medido contra la misma tabla sin disparador."""
    from sqlalchemy import text
    with db.begin() as c:
        c.execute(text('CREATE TABLE IF NOT EXISTS g_bench (id int PRIMARY KEY, v int)'))
    rid6 = _alert(db, 'g-al-6')

    def bench(table, guarded, n=300):
        t0 = time.perf_counter()
        with db.begin() as c:
            if guarded:
                c.execute(text("SELECT set_config('khipus.decision_id', '00000000-0000-0000-0000-000000000001', true)"))
            for i in range(n):
                if table == 'alerts':
                    c.execute(text('UPDATE alerts SET is_active = (:i % 2 = 0) WHERE id = CAST(:r AS uuid)'),
                              {'i': i, 'r': rid6})
                else:
                    c.execute(text('INSERT INTO g_bench (id, v) VALUES (1, :i) ON CONFLICT (id) DO UPDATE SET v = :i'),
                              {'i': i})
        return (time.perf_counter() - t0) / n * 1000
    with_guard = min(bench('alerts', True) for _ in range(3))
    without = min(bench('g_bench', False) for _ in range(3))
    with db.begin() as c:
        c.execute(text('DROP TABLE IF EXISTS g_bench'))
    print(f'\nguardia: {with_guard:.3f} ms/UPDATE con disparador · {without:.3f} ms sin disparador')
    assert with_guard < without + 1.0


@needs_db
def test_base_del_codigo_anterior_recibe_la_guardia(db):
    """Emula una base creada por el código desplegado ANTES del paso 22/26: sin guardia, sin sus tablas y con la
    guardia de blobs vieja. ensure_all (arranque) la instala sin tocar datos y el libro sigue verificando."""
    from sqlalchemy import text

    from core import ledger, ledger_ddl, ledger_guard
    ledger.seal(db)
    assert ledger.verify(engine=db)['ok']
    with db.begin() as c:
        for t in ledger_guard.GUARD_TABLES:
            c.execute(text(f'DROP TRIGGER IF EXISTS {t}_kh_guard ON {t}'))
            c.execute(text(f'DROP TRIGGER IF EXISTS {t}_kh_guard_commit ON {t}'))
        c.execute(text('DROP FUNCTION IF EXISTS kh_require_decision()'))
        c.execute(text('DROP FUNCTION IF EXISTS kh_require_decision_commit()'))
        c.execute(text('DROP TABLE IF EXISTS kh_guard_violations'))
        c.execute(text('DROP TABLE IF EXISTS kh_guard_modes'))
    with db.connect() as c:
        assert not any(ledger_guard.triggers_present(c).values())
    assert ledger_ddl.ensure_all(db)
    with db.connect() as c:
        assert all(ledger_guard.triggers_present(c).values())
        assert c.execute(text('SELECT mode FROM kh_guard_modes ORDER BY id DESC LIMIT 1')).scalar() in ('warn',
                                                                                                       'enforce')
    ledger.seal(db)
    assert ledger.verify(engine=db)['ok']
