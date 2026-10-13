"""tests/test_gates_resulting_state.py — INFRA_OPERATIVA paso 10: puertas de la ontología en SOMBRA.

El sondeo de MAP G (docs/INFRA_OPERATIVA.md §3, §9) — escrituras no conformes que hoy se ACEPTAN en silencio —
ahora queda REGISTRADO con su regla (decision_violations + GateReport/1 con mensaje ES/EN), sin rechazar nada
(modo sombra: todo avisa; el paso 11 bloqueará):
  · ProponerVinculo con autovínculo, `tipo="suministra_a"`, peso 7,5 / confianza 3 y un campo desconocido `peso`;
  · severidad fuera de escala sobre el ESTADO RESULTANTE (ActivarFactor sin severidad toma severity_crisis);
  · CorregirDato `severity="alto"` sobre un Factor;
  · evento crudo (sin decisión en curso) con `rel=foo` / `weight=-3` → una decisión audit.gates al confirmar;
  · CrearFactor NO da "sin miembros" (el factor se evalúa con su estado FINAL de la transacción);
  · G-BULK evalúa el lote una vez (G1 no se repite); G-PROP deja el reporte en la propuesta;
  · G2 con aplicación automática fuera de SAFE_AUTO; G8 sobre la propia ficha;
  · presupuesto: la puerta compilada < 1 ms p95 (medido; objetivo de diseño 0,3 ms); KHIPU_GATES=off la apaga.
"""
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from core import governance
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    governance._reset_for_tests()
    assert init_schema(retries=1)
    with session_scope() as s:
        for oid, t in (('TSMC', 'Company'), ('APPLE', 'Company'), ('NVDA', 'Company'), ('PERU', 'Country')):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': t}, valid_from='2000-01-01', source='test',
                        actor='pytest', object_id=oid)
    yield engine
    governance._reset_for_tests()
    Base.metadata.drop_all(engine)


def _act(action, payload, principal=None):
    from core import identity
    from ontology.actions import execute_action
    from ontology.db import session_scope
    meta = {}
    with session_scope() as s:
        out = execute_action(s, action, payload, 'op:fabrizio', principal=principal or identity.operator(),
                             meta=meta)
    return meta['decision_id'], out


def _viol(engine, decision_id):
    from sqlalchemy import text
    with engine.connect() as c:
        rows = c.execute(text('SELECT rule_iri, severity, focus, value FROM decision_violations '
                              'WHERE decision_id = CAST(:d AS uuid) ORDER BY ord'), {'d': decision_id}).all()
        dec = c.execute(text('SELECT verdict, manifest, status FROM decisions WHERE id = CAST(:d AS uuid)'),
                        {'d': decision_id}).first()
    return rows, dec


@needs_db
def test_autovinculo_y_relacion_fuera_del_vocabulario_quedan_registrados(db):
    did, out = _act('ProponerVinculo', {'from_id': 'TSMC', 'to_id': 'TSMC', 'tipo': 'suministra_a',
                                        'metadata': {'weight': 7.5, 'confidence': 3}, 'fuente': 'prueba',
                                        'peso': 9})
    assert out['status'] == 'proposed' and out['link_id']          # SOMBRA: la escritura NO se rechaza
    rows, dec = _viol(db, did)
    rules = {r.rule_iri for r in rows}
    assert {'khr:link.no_self_loop', 'khr:link.rel_in_vocab', 'khr:link.weight_range',
            'khr:link.confidence_range', 'khr:action.no_unknown_fields'} <= rules
    assert all(r.severity in ('warn', 'info') for r in rows)          # todo AVISA en sombra
    self_loop = next(r for r in rows if r.rule_iri == 'khr:link.no_self_loop')
    v = self_loop.value
    assert v['declared'] == 'block' and v['mode'] == 'shadow' and v['gate'] == 'ontology.g1.link'
    assert 'TSMC' in v['message']['es'] and 'TSMC' in v['message']['en']
    w = next(r for r in rows if r.rule_iri == 'khr:link.weight_range').value
    assert w['value'] == 7.5 and w['limit'] == 6.0 and '7,5' in w['message']['es'] and '7.5' in w['message']['en']
    assert dec.verdict['outcome'] == 'warn' and dec.status == 'executed'
    gr = dec.manifest['gate_reports']
    assert {g['gate'] for g in gr} >= {'ontology.g1.link', 'ontology.g2.action'}
    assert all(len(g['ir_hash']) == 64 and g['mode'] == 'shadow' for g in gr)
    from core.gates import engine
    assert all(r.value is not None for r in rows) and rows[0].value['shapes_semver'] == '1.0.0'
    assert engine.state()['available'] and engine.state()['rules'] == 31


@needs_db
def test_blob_gate_report_completo(db):
    import json
    import zlib

    from sqlalchemy import text
    did, _ = _act('ProponerVinculo', {'from_id': 'APPLE', 'to_id': 'APPLE', 'tipo': 'supply', 'fuente': 'x'})
    _rows, dec = _viol(db, did)
    sha = next(g['blob'] for g in dec.manifest['gate_reports'] if g['gate'] == 'ontology.g1.link')
    with db.connect() as c:
        body = c.execute(text('SELECT body FROM decision_blobs WHERE sha256 = :s'), {'s': sha}).scalar()
    rep = json.loads(zlib.decompress(bytes(body)))
    assert rep['schema'] == 'gate-report/1' and rep['shapes']['artifact'] == 'ontology.shapes'
    assert rep['results'][0]['message']['es'] and rep['results'][0]['message']['en']


@needs_db
def test_factor_estado_resultante_y_severidad(db):
    did, out = _act('CrearFactor', {'label': 'Escasez HBM', 'severity': 3, 'affects': ['NVDA', 'TSMC'],
                                    'razon': 'prueba'})
    rows, _ = _viol(db, did)
    assert 'khr:factor.has_live_members' not in {r.rule_iri for r in rows}     # estado FINAL: tiene miembros
    fid = out['factor_id']
    did2, _ = _act('CorregirDato', {'object_id': fid, 'campo': 'severity_crisis', 'valor_nuevo': 12,
                                    'fuente': 'prueba'})
    assert 'khr:factor.severity_scale' in {r.rule_iri for r in _viol(db, did2)[0]}
    did3, res = _act('ActivarFactor', {'factor_id': fid, 'razon': 'crisis'})
    assert res['severity'] == 12.0                                   # G-2: el estado resultante queda en 12
    rows3 = _viol(db, did3)[0]
    sc = [r for r in rows3 if r.rule_iri == 'khr:factor.severity_scale']
    assert sc and sc[0].value['value'] == 12.0 and sc[0].value['limit'] == 10.0
    did4, _ = _act('CorregirDato', {'object_id': fid, 'campo': 'severity', 'valor_nuevo': 'alto', 'fuente': 'x'})
    assert {'khr:object.numeric_props', 'khr:factor.severity_scale'} <= {r.rule_iri for r in _viol(db, did4)[0]}


@needs_db
def test_evento_crudo_sin_decision_queda_en_audit_gates(db):
    from sqlalchemy import text

    from ontology.db import session_scope
    from ontology.service import apply_event
    with db.connect() as c:
        before = c.execute(text("SELECT count(*) FROM decisions WHERE kind = 'audit.gates'")).scalar()
    with session_scope() as s:
        apply_event(s, 'LinkCreated', {'rel_type': 'foo', 'weight': -3}, valid_from='2026-01-01', source='raw',
                    actor='pytest', object_id='APPLE', target_id='NVDA')
    with db.connect() as c:
        rows = c.execute(text(
            "SELECT d.id, d.principal_id, d.durability, v.rule_iri FROM decisions d JOIN decision_violations v "
            "ON v.decision_id = d.id WHERE d.kind = 'audit.gates' ORDER BY d.seq DESC")).all()
        after = c.execute(text("SELECT count(*) FROM decisions WHERE kind = 'audit.gates'")).scalar()
        n_link = c.execute(text("SELECT count(*) FROM links WHERE rel_type = 'foo'")).scalar()
    assert n_link == 1                                                  # sombra: se escribió
    assert after == before + 1
    last = rows[0].id
    rules = {r.rule_iri for r in rows if r.id == last}
    assert {'khr:link.rel_in_vocab', 'khr:link.weight_range'} <= rules
    assert rows[0].principal_id == 'system:gates' and rows[0].durability == 'async'


@needs_db
def test_rollback_no_deja_aviso(db):
    from sqlalchemy import text

    from ontology.db import session_scope
    from ontology.service import apply_event
    with db.connect() as c:
        before = c.execute(text("SELECT count(*) FROM decisions WHERE kind = 'audit.gates'")).scalar()
    with pytest.raises(RuntimeError):
        with session_scope() as s:
            apply_event(s, 'LinkCreated', {'rel_type': 'bar'}, valid_from='2026-01-01', source='raw',
                        actor='pytest', object_id='APPLE', target_id='NVDA')
            raise RuntimeError('se deshace')
    with db.connect() as c:
        assert c.execute(text("SELECT count(*) FROM decisions WHERE kind = 'audit.gates'")).scalar() == before


@needs_db
def test_auto_aplicacion_fuera_de_safe_auto(db):
    from core import identity
    did, _ = _act('CrearTesis', {'company_id': 'NVDA', 'stance': 'long', 'confidence': 0.7,
                                 'rationale': 'Demanda de IA sostenida'},
                  principal=identity.system('auto_apply'))
    rows = _viol(db, did)[0]
    r = [x for x in rows if x.rule_iri == 'khr:action.auto_apply_allowed']
    assert r and r[0].value['value'] == 'CrearTesis'


@needs_db
def test_g_bulk_un_reporte_por_lote(db):
    from sqlalchemy import text

    from ontology.bulk_import import import_links_bulk
    from ontology.db import session_scope
    with db.connect() as c:
        before = c.execute(text("SELECT count(*) FROM decisions WHERE kind = 'audit.gates'")).scalar()
    with session_scope() as s:
        out = import_links_bulk(s, [{'source': 'APPLE', 'target': 'TSMC', 'rel_type': 'supply', 'weight': 9},
                                    {'source': 'NVDA', 'target': 'TSMC', 'rel_type': 'supply', 'weight': 2}],
                                provenance='wikidata')
    assert out['created'] == 2 and out['gate']['checked'] == 2 and out['gate']['mode'] == 'shadow'
    assert out['gate']['by_rule'].get('khr:link.weight_range') == 1
    with db.connect() as c:
        rows = c.execute(text(
            "SELECT d.id, count(v.*) FROM decisions d JOIN decision_violations v ON v.decision_id = d.id "
            "WHERE d.kind = 'audit.gates' GROUP BY d.id, d.seq ORDER BY d.seq DESC")).all()
        after = c.execute(text("SELECT count(*) FROM decisions WHERE kind = 'audit.gates'")).scalar()
    assert after == before + 1                                          # UNA decisión para el lote (G1 no repite)


@needs_db
def test_g_prop_deja_el_reporte_en_la_propuesta(db):
    from ontology.agents import _gate_prop
    from ontology.db import session_scope
    with session_scope() as s:
        rep = _gate_prop(s, 'Cartografo', {'action_type': 'ProponerVinculo', 'confidence': 0.9,
                                          'payload': {'from_id': 'PERU', 'to_id': 'NVDA', 'tipo': 'supply',
                                                      'fuente': 'agente'}})
        rep2 = _gate_prop(s, 'Cartografo', {'action_type': 'CrearTesis', 'confidence': 0.9,
                                           'payload': {'company_id': 'NVDA'}})
    assert rep['mode'] == 'shadow'
    assert 'khr:link.flow_supplier_type' in {r['rule'] for r in rep['results']}
    assert 'khr:action.agent_needs_human' in {r['rule'] for r in rep2['results']}
    r = next(x for x in rep2['results'] if x['rule'] == 'khr:action.agent_needs_human')
    assert r['severity'] == 'requires_approval' and r['effective'] == 'warn' and r['message']['en']


@needs_db
def test_g8_cotizacion_sin_fecha(db):
    from core import decisions, identity
    from ontology.db import session_scope
    with session_scope() as s:
        with decisions.decision_scope('policy.change', identity.operator(), session=s, subject={'t': 1}) as ctx:
            ctx.quote({'ticker': 'NVDA', 'px': 180.0})
            ctx.status = 'executed'
        did = str(ctx.id)
    rows = _viol(db, did)[0]
    assert [r.rule_iri for r in rows] == ['khr:decision.quotes_have_asof_src']
    assert rows[0].value['gate'] == 'ledger.g8'


def test_latencia_de_la_puerta_compilada():
    import core.gates as gates
    from core.gates import focus as F
    eps = {f'N{i}': {'type': 'Company', 'live': True} for i in range(40)}
    inv = [{'id': f'R{i}', 'source': 'N1', 'target': 'N0', 'rel': 'supply', 'live': True} for i in range(5)]
    t, f = F.link_triples({'id': 'L', 'source': 'N0', 'target': 'N1', 'rel': 'supply', 'weight': 3, 'confidence': 0.9,
                           'valid_from': '2024-01-01', 'rel_label': 'provee'}, eps, inv, {},
                          {'max_weight': 6.0, 'high_conf_min': 0.5, 'min_trust': 2}, ('supply',))
    lat = []
    for _ in range(400):
        t0 = time.perf_counter()
        rep = gates.evaluate('bench', t, f)
        lat.append((time.perf_counter() - t0) * 1e6)
    lat.sort()
    p50, p95 = lat[200], lat[380]
    print(f'puerta compilada (vínculo, {len(t)} tripletas): p50 {p50:.0f} µs · p95 {p95:.0f} µs')
    assert rep['results'] and p95 < 1000


def test_interruptor_de_emergencia(monkeypatch):
    import core.gates as gates
    from core.gates import focus as F
    t, f = F.object_triples({'id': 'X', 'type': 'Widget', 'props': {}})
    assert gates.evaluate('x', t, f)['results']
    monkeypatch.setenv('KHIPU_GATES', 'off')
    assert gates.mode() == 'off' and gates.evaluate('x', t, f) is None
