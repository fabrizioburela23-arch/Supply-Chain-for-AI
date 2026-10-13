"""tests/test_cierre_defectos.py — los defectos que encontró la auditoría de cierre del lote H (docs/CIERRE_INFRA.md §4)
y la revisión del replay, cada uno con la prueba que fallaba antes del arreglo:

  E1  POST /api/ontology/events deja `ontology.raw_event` (misma transacción)            (también en test_cierre_infra)
  E3  POST /api/ontology/ingest/news deja `ontology.news_ingest` (noop si nada es nuevo)
  E4  POST /api/matrix/simulations deja `simulation.save`                                 (también en test_cierre_infra)
  E5  RESEARCH_CALIBRATION_K / RESEARCH_OUTCOME_BAND / BROKERAGE_APPROVAL_TTL_MIN ya no cambian números (D2) y avisan
  E6  `import ontology.ledger_models` primero ya no falla (tipos en ontology/sqltypes.py)
  E8  un replay SIN autenticar (GET o POST) no deja `audit.replay`; con PIN, una por auditor/decisión/veredicto/día
  R2  «¿Por qué?» sin PIN no muestra el ticker de órdenes ni memos (solo cuántas cotizaciones)
  R3  un qué-pasaría-si por el camino directo (GRAPH ASOF) guarda la versión del grafo LEÍDA al calcular: un hecho
      confirmado antes de que el libro escriba la ficha ya no da un falso «distinto»
  R5  mcp.tool_call / chat.route sin llamadas de IA no se explican como «texto de la IA»; portfolio_advice = datos en vivo
  R6  un blob de desborde purgado da «no repetible» (blob_purged), nunca un «distinto» inventado
  U1  «idéntica» + «aproximada» explica POR QUÉ es aproximada (ES/EN) y engine/audit.js lo muestra con su «?»
  (E2 reconcile apply/rollback: tests/test_reconcile.py)
Sin red.
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

from tests.test_replay_determinism import PIN, _ev, _flush, _last, _replay, client, db  # noqa: E402,F401

needs_db = pytest.mark.skipif(not os.getenv('DATABASE_URL', ''), reason='requiere DATABASE_URL (Postgres)')


def _count(sql, **kw):
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        return s.execute(text(sql), kw).scalar()


# ── sin base ─────────────────────────────────────────────────────────────────────────────────────────────────────
def test_e6_ledger_models_se_importa_primero():
    for mod in ('ontology.ledger_models', 'ontology.governance_models', 'ontology.history_models'):
        r = subprocess.run([sys.executable, '-c', f'import {mod}'], cwd=ROOT, capture_output=True, text=True,
                           env=dict(os.environ, PYTHONPATH=ROOT))
        assert r.returncode == 0, (mod, r.stderr[-400:])


def test_e5_variables_viejas_no_mandan_y_el_diagnostico_avisa(monkeypatch):
    from brokerage import service
    from core import governance
    from research import outcomes
    monkeypatch.setenv('RESEARCH_CALIBRATION_K', '1000')
    monkeypatch.setenv('RESEARCH_OUTCOME_BAND', '0.07')
    monkeypatch.setenv('BROKERAGE_APPROVAL_TTL_MIN', '5')
    assert outcomes.k_default() == 10.0 and outcomes.band_default() == 0.02
    assert service.approval_ttl_s() == 1440 * 60
    warn = {w['env'] for w in governance.env_warnings()}
    assert {'RESEARCH_CALIBRATION_K', 'RESEARCH_OUTCOME_BAND', 'BROKERAGE_APPROVAL_TTL_MIN'} <= warn
    # los números viven en artefactos versionados (MINOR que solo agrega claves, con los valores de hoy)
    assert governance.param('policy.committee', 'calibration_k') == 10.0
    assert governance.param('policy.committee', 'outcome_band') == 0.02
    assert governance.param('policy.broker_risk', 'approval_ttl_min') == 1440


def test_e5_con_un_release_anterior_sin_la_clave_rige_el_valor_del_codigo(monkeypatch):
    from core import governance
    from research import outcomes
    real = governance.param

    def old_release(aid, key, default=governance._MISSING):
        if key in ('calibration_k', 'outcome_band', 'approval_ttl_min'):
            if default is governance._MISSING:
                raise governance.GovernanceError('sin la clave')
            return default
        return real(aid, key, default)
    monkeypatch.setattr(governance, 'param', old_release)
    monkeypatch.setenv('RESEARCH_CALIBRATION_K', '3')
    assert outcomes.k_default() == 10.0
    assert any(w['env'] == 'RESEARCH_CALIBRATION_K' and w['in_force'] == 10.0 for w in governance.env_warnings())


def test_u1_audit_js_explica_la_aproximacion_en_dos_idiomas():
    js = open(os.path.join(ROOT, 'engine', 'audit.js'), encoding='utf-8').read()
    assert "chip('audit_approx')" in js and 'approximations_text' in js
    assert "'Por qué es aproximada: '" in js and "'Why it is approximate: '" in js
    ex = open(os.path.join(ROOT, 'engine', 'explain.js'), encoding='utf-8').read()
    i = ex.index('audit_approx:')
    blk = ex[i:i + 2500]
    assert "es: { t: '¿Qué significa «aproximada»?'" in blk and "en: { t: 'What does \"approximate\" mean?'" in blk
    from core import replay
    for code, (es, en) in replay.APPROX_LABELS.items():
        assert es and en and es != en, code
    r = subprocess.run(['node', '--check', os.path.join(ROOT, 'engine', 'audit.js')], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


# ── con base ─────────────────────────────────────────────────────────────────────────────────────────────────────
W = {}


@needs_db
def test_preparar_decisiones(db, client):
    r = client.post('/api/hot/scenario', json={'shocks': [{'id': 'RA', 'magnitude': 0.9}]})
    assert r.status_code == 200, r.get_json()
    _flush()
    W['scn'] = _last('whatif.shock')


@needs_db
def test_e8_replay_anonimo_no_deja_audit_replay_y_con_pin_una_sola(db, client):
    from core import replay
    did = W['scn']
    q = "SELECT count(*) FROM decisions WHERE kind = 'audit.replay' AND subject->>'target_id' = :d"
    a0 = _count(q, d=did)
    for i in range(4):                                   # GET y POST sin PIN, con y sin caché
        replay.cache_clear()
        r = (client.get if i % 2 else client.post)(f'/api/ledger/replay/{did}')
        assert r.status_code == 200 and r.get_json()['redacted'] is True
    _flush()
    assert _count(q, d=did) == a0, 'una lectura anónima no agranda el libro sellado'
    assert _count("SELECT count(*) FROM decision_outcomes WHERE outcome_kind = 'replay' AND "
                  "decision_id = CAST(:d AS uuid)", d=did) >= 1           # el resultado deduplicado sí queda
    for i in range(3):                                   # con PIN: UNA por auditor, decisión, veredicto y día
        if i == 1:
            replay.cache_clear()
        r = client.post(f'/api/ledger/replay/{did}', headers={'X-Trade-Pin': PIN})
        assert r.status_code == 200 and r.get_json()['redacted'] is False
    _flush()
    assert _count(q, d=did) == a0 + 1
    replay.cache_clear()                                 # tras un «reinicio» (memoria vacía) manda la base
    assert client.post(f'/api/ledger/replay/{did}', headers={'X-Trade-Pin': PIN}).status_code == 200
    _flush()
    assert _count(q, d=did) == a0 + 1


@needs_db
def test_r2_por_que_sin_pin_no_muestra_el_ticker(db, client):
    from core import decisions, identity
    from ontology.db import session_scope
    ctx = decisions.DecisionCtx('order.preview', identity.system('pytest_order'), subject={'symbol': 'AMD'})
    ctx.quote({'ticker': 'AMD', 'src': 'alpaca_trade', 'as_of': '2026-10-13T11:38:17Z', 'price': 160.0})
    ctx.output = {'ok': True}
    with session_scope() as s:
        decisions.record(s, ctx, status='executed')
    did = str(ctx.id)
    j = client.get(f'/api/ledger/why/{did}').get_json()
    assert j['redacted'] is True and 'quotes' not in j and j['n_quotes'] == 1
    assert 'AMD' not in json.dumps(j)
    j2 = client.get(f'/api/ledger/why/{did}', headers={'X-Trade-Pin': PIN}).get_json()
    assert j2['redacted'] is False and j2['quotes'][0]['ticker'] == 'AMD'


@needs_db
def test_r3_camino_directo_guarda_la_version_leida_al_calcular(db, client, monkeypatch):
    from core import decisions
    held = []
    monkeypatch.setattr(decisions, 'submit_async', lambda build, status='recorded': held.append((build, status)) or True)
    r = client.post('/api/matrix/impact', json={'shock': ['RA'], 'as_of': '2026-01-01'})
    assert r.status_code == 200, r.get_json()
    from ontology.db import session_scope
    with session_scope() as s:                           # otro hecho se confirma ANTES de que el libro escriba la ficha
        _ev(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 6}, 'RA', 'RD')
    monkeypatch.undo()
    for b, st in held:
        decisions._run_async_item(b, st)
    did = _last('whatif.shock')
    out = _replay(did)
    codes = [a['code'] for a in out['approximations']]
    assert out['verdict'] == 'identical', (out['verdict'], out['reasons'], out['steps'])
    assert 'graph_version_from_stamp' not in codes and 'as_of_direct_path' in codes
    # U1: idéntica + aproximada explica POR QUÉ (y ya no dice «EXACTAMENTE»)
    assert out['fidelity'] == 'approximate'
    assert 'APROXIMADA' in out['explanation']['es'] and 'APPROXIMATE' in out['explanation']['en']
    assert 'EXACTAMENTE' not in out['explanation']['es']
    assert any(a['code'] == 'as_of_direct_path' and a['es'] and a['en'] for a in out['approximations_text'])


@needs_db
def test_r5_sin_llamadas_de_ia_no_se_dice_texto_de_ia(db):
    from core import decisions, identity
    from ontology.db import session_scope
    got = {}
    for kind in ('mcp.tool_call', 'chat.route', 'committee.portfolio_advice'):
        ctx = decisions.DecisionCtx(kind, identity.system('pytest_r5'), subject={'tool': 'get_company'})
        ctx.output = {'status': 'ok'}
        with session_scope() as s:
            decisions.record(s, ctx, status='executed')
        got[kind] = _replay(str(ctx.id))
    assert got['mcp.tool_call']['reasons'] == ['no_deterministic_core'], got['mcp.tool_call']['reasons']
    assert 'texto escrito por la IA' not in got['mcp.tool_call']['explanation']['es']
    assert 'external_model' in got['chat.route']['reasons'] and 'ai_text' not in got['chat.route']['reasons']
    assert 'live_data' in got['committee.portfolio_advice']['reasons']
    assert all(o['verdict'] == 'not_replayable' for o in got.values())


@needs_db
def test_r6_desborde_purgado_es_no_repetible(db, monkeypatch):
    from core import decisions, identity
    from core import replay as R
    from ontology.db import session_scope
    ctx = decisions.DecisionCtx('whatif.shock', identity.system('pytest_r6'), subject={'entity_ids': ['RA']})
    ctx.params(endpoint='/api/hot/scenario', shocks=[{'id': f'RA_{i:05d}_' + 'x' * 60, 'magnitude': 1.0}
                                                     for i in range(260)])
    ctx.output = {'top': [['RA', 100.0]], 'n': 1, 'content_sha': '0' * 64}
    with session_scope() as s:
        decisions.record(s, ctx, status='executed')
    d = _replay(str(ctx.id))
    ob = None
    from sqlalchemy import text
    with session_scope() as s:
        ob = s.execute(text('SELECT manifest->>\'overflow_blob\' FROM decisions WHERE id = CAST(:d AS uuid)'),
                       {'d': str(ctx.id)}).scalar()
    assert ob, 'la prueba necesita un manifiesto desbordado'
    real = R._blob
    monkeypatch.setattr(R, '_blob', lambda session, sha: (None, 'purged') if sha == ob else real(session, sha))
    R.cache_clear()
    d = _replay(str(ctx.id))
    assert d['verdict'] == 'not_replayable', (d['verdict'], d['reasons'])
    assert 'blob_purged' in d['reasons'] and not any(s['name'] == 'deterministic_core' for s in d['steps'])
    assert '90' in d['explanation']['es']


@needs_db
def test_e1_e3_e4_escrituras_con_su_decision(db, client, monkeypatch):
    from ontology.db import session_scope
    with session_scope() as s:
        _ev(s, 'ObjectCreated', {'label': 'Noticias Co', 'type': 'Company', 'properties': {}}, 'NewsCo')

    class _Prov:
        name = 'stub'

        def get_latest(self, term, limit=10):
            return [{'url': 'https://example.com/nota-cierre-h', 'title': 'Nota', 'publisher': 'Ejemplo',
                     'published_at': '2026-10-10T00:00:00Z', 'provider': 'stub'}]

    class _Reg:
        def configured(self):
            return [_Prov()]
    import core.providers.news as N
    monkeypatch.setattr(N, 'news_registry', lambda: _Reg())
    q = "SELECT count(*) FROM decisions WHERE kind = :k AND status = :st"
    n0 = _count(q, k='ontology.news_ingest', st='executed')
    r = client.post('/api/ontology/ingest/news', json={'entity_id': 'NewsCo', 'actor': 'pytest'})
    assert r.status_code == 200 and r.get_json()['decision_id'], r.get_json()
    assert _count(q, k='ontology.news_ingest', st='executed') == n0 + 1
    r = client.post('/api/ontology/ingest/news', json={'entity_id': 'NewsCo', 'actor': 'pytest'})
    assert r.status_code == 200
    assert _count(q, k='ontology.news_ingest', st='noop') >= 1, 'la segunda vez nada es nuevo → noop'
    r = client.post('/api/matrix/simulations', json={'name': 'cierre-h', 'targets': ['RA'], 'affected': 2})
    assert r.status_code == 200 and r.get_json()['decision_id']
    did = r.get_json()['decision_id']
    assert _count("SELECT count(*) FROM decision_refs WHERE decision_id = CAST(:d AS uuid) AND role = 'effect'",
                  d=did) == 1
    r = client.post('/api/ontology/events', headers={'X-Trade-Pin': PIN}, json={
        'actor': 'pytest', 'event_type': 'ObjectUpdated', 'object_id': 'NewsCo', 'valid_from': '2026-10-13',
        'source': 'pytest', 'payload': {'properties': {'country': 'PE'}}})
    assert r.status_code == 200 and r.get_json()['decision_id'], r.get_json()
    assert _count(q, k='ontology.raw_event', st='executed') >= 1
