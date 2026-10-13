"""tests/test_review_lists.py — BRECHAS_V2 bloque 5: listas de revisión del grafo para Fabrizio (decisiones #6 #7 #8 #10).

`scripts/build_graph_review.py` lee el catálogo y PROPONE (nada se aplica): docs/REVISION_GRAFO.md (✔/✘ en español
simple) + docs/revision_grafo.json (`graph-review/1`, insumo de un paso futuro). Estas pruebas fijan:
  · documento y JSON al día y deterministas (misma entrada → mismos bytes);
  · los conteos coinciden con su fuente independiente: la regla de la migración (27 hechos fechados), el trinquete de
    scripts/audit_graph.py (`text_direction`, L3-12), el histograma de pesos del snapshot (462 con peso 1, 400 < 1, 41
    proveedores únicos) y LAS PUERTAS SHACL compiladas (58 relaciones fuera de vocabulario = `link.rel_in_vocab`,
    12 márgenes = `object.margin_range`);
  · casos concretos de cada regla (y contraejemplos: el texto escrito desde el cliente NO es una dirección al revés);
  · ninguna fecha inventada y ningún camino de escritura (el script no aplica nada; `--db` es solo lectura).
Sin Node.js las pruebas que necesitan el origen de cada fila se saltan solas. Sin red; sin base salvo la última.
"""
import collections
import json
import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts import audit_graph as AG  # noqa: E402
from scripts import build_graph_review as GR  # noqa: E402

needs_node = pytest.mark.skipif(shutil.which('node') is None, reason='Node.js no instalado')


@pytest.fixture(scope='module')
def snap():
    return GR.load_snapshot()


@pytest.fixture(scope='module')
def origins():
    if shutil.which('node') is None:
        pytest.skip('Node.js no instalado')
    return GR.load_origins()


@pytest.fixture(scope='module')
def rv(snap, origins):
    return GR.build(snap, origins)


# ── al día y determinista ────────────────────────────────────────────────────────────────────────────────────────
@needs_node
def test_documento_y_json_al_dia():
    assert GR.main(['--check']) == 0, 'corre: python scripts/build_graph_review.py'


@needs_node
def test_determinista(snap, origins, rv):
    again = GR.build(snap, origins)
    assert GR.render_md(again) == GR.render_md(rv)
    assert GR.render_json(again) == GR.render_json(rv)
    js = json.loads(GR.render_json(rv))
    assert js['format'] == 'graph-review/1'
    assert 'generated_at' not in js            # nada que cambie entre corridas


# ── (a) los 27 vínculos fechados ─────────────────────────────────────────────────────────────────────────────────
def _migration_dated(snap):
    """La regla de scripts/migrate_v0_to_ontology.py (hecho-arista sin rel → 'supply' sin peso), escrita aparte."""
    known = {n['id'] for n in snap['nodes']} | {o['id'] for o in snap['ontology']['objects']}
    return [f for f in snap['temporal_facts'] if f.get('object_type') == 'node' and not f.get('rel')
            and f['subject'] in known and f['object'] in known and f['subject'] != f['object']]


@needs_node
def test_a_los_27_fechados_con_tipo_y_direccion(snap, rv):
    mig = _migration_dated(snap)
    assert len(mig) == 27 == rv['counts']['dated_links']
    assert [d['fact_id'] for d in rv['a_dated_links']] == [f['id'] for f in mig]
    by = {d['fact_id']: d for d in rv['a_dated_links']}
    assert all(d['rule'] != 'unmatched' for d in by.values()), [d['fact_id'] for d in by.values() if d['rule'] == 'unmatched']
    vocab = AG.load_vocab()
    for d in by.values():
        p = d['proposal']
        assert p['kind'] in ('retract', 'create', 'date_existing')
        if p['kind'] != 'retract':
            assert p['type'] in vocab['rel_types'] and p['type'] != 'supply' or d['rule'] in ('supply', 'gpus_de', 'co_design')
        assert d['fact_file'] and d['fact_file'].startswith('nodes/'), d['fact_id']
        assert d['actions'][0]['action'] == 'RetractarVinculo'
        assert d['actions'][0]['match']['rel_type'] == 'supply' and d['actions'][0]['match']['channel'] == 'migration_v0_temporal'
    # los casos de BRECHAS L3-02
    assert (by['tf_stargate']['proposal']['source'], by['tf_stargate']['proposal']['target'],
            by['tf_stargate']['proposal']['type']) == ('Oracle', 'OpenAI', 'cloud')
    assert by['tf_xai_colossus']['proposal']['source'] == 'Nvidia' and by['tf_xai_colossus']['proposal']['inverted']
    assert by['tf_google_kairos']['proposal'] == {**by['tf_google_kairos']['proposal'], 'source': 'KairosPower',
                                                  'target': 'Alphabet', 'type': 'ppa', 'inverted': True}
    assert by['tf_oklo_meta_ppa']['proposal']['source'] == 'Oklo' and not by['tf_oklo_meta_ppa']['proposal']['inverted']
    for fid in ('tf_msft_openai', 'tf_amazon_anthropic', 'tf_meta_scale', 'tf_nvidia_invests_intel', 'tf_stargate_sb'):
        assert by[fid]['proposal']['type'] == 'invest', fid
    assert by['tf_qualcomm_huawei_loss']['proposal']['kind'] == 'retract'
    assert by['tf_tsmc_supplies_nvidia']['proposal']['type'] == 'fab'
    # "ya existe" de verdad en el catálogo
    trip = {(l['source'], l['target'], l['type']) for l in snap['links']}
    for d in by.values():
        p = d['proposal']
        if p['kind'] == 'date_existing':
            assert (p['source'], p['target'], p['type']) in trip
        elif p['kind'] == 'create':
            assert (p['source'], p['target'], p['type']) not in trip


# ── (b) direcciones contrarias al texto: el MISMO trinquete de audit_graph ───────────────────────────────────────
@needs_node
def test_b_direcciones_por_texto_igual_al_trinquete(snap, rv):
    base = AG.load_baseline()
    res = AG.audit_snapshot(snap)
    n = res['metrics']['text_direction']
    assert n == len(rv['b_text_directions']) == rv['counts']['text_directions']
    assert n <= base['metrics']['text_direction']
    assert 9 <= rv['counts']['text_directions_new'] <= 15     # BRECHAS L3-12: "al menos 9 claros fuera de los 32"
    got = {(d['source'], d['target']): d for d in rv['b_text_directions']}
    for pair in (('OpenAI', 'Nvidia'), ('Snowflake', 'Nvidia'), ('Qwen', 'Nvidia'), ('BostonDynamics', 'OpenAI'),
                 ('Tesla', 'OpenAI'), ('Samsung', 'SKHynix'), ('Data4', 'Brookfield'), ('DSV', 'MSC')):
        assert pair in got, pair
    assert got[('Palantir', 'Amazon')]['new_type'] == 'cloud'          # "corre sobre AWS" = nube
    assert got[('ODATA', 'AlignedDataCenters')]['proposal'] == 'retract_reverse_exists'
    # revisión: el inverso existe con el tipo NUEVO (Amazon → Palantir 'cloud') → no se propone un duplicado
    b02 = got[('Palantir', 'Amazon')]
    assert b02['proposal'] == 'retract_reverse_exists' and b02['reverse_type'] == 'cloud'
    assert [a['action'] for a in b02['actions']] == ['RetractarVinculo']
    assert got[('Tesla', 'OpenAI')]['proposal'] == 'retract'
    # contraejemplos: escrito desde el CLIENTE (correcto), "USA" (país), voz pasiva, el comprador es el source
    for pair in (('MediaTek', 'Samsung'), ('Nvidia', 'Tesla'), ('Urenco', 'Constellation'), ('Trimble_Inc', 'Boeing'),
                 ('SoftBank', 'berkshire-grey'), ('Thales', 'Imperva'), ('Amazon', 'Anthropic'), ('KEPCO', 'Samsung')):
        assert pair not in got, pair


def test_detector_de_texto_sintetico():
    snap = {
        'nodes': [{'id': i, 'label': i, 'cat': 'fabless', 'sector': 'diseno'} for i in ('Alfa', 'Beta', 'Gama', 'Delta')],
        'links': [
            {'source': 'Alfa', 'target': 'Beta', 'w': 3, 'type': 'supply', 'rel': 'Alfa usa chips de Beta'},       # al revés
            {'source': 'Beta', 'target': 'Alfa', 'w': 3, 'type': 'supply', 'rel': 'Alfa usa chips de Beta'},       # correcto
            {'source': 'Gama', 'target': 'Delta', 'w': 3, 'type': 'supply', 'rel': 'Los chips de Gama se usan en Delta'},
            {'source': 'Gama', 'target': 'Alfa', 'w': 2, 'type': 'cloud', 'rel': 'Infra de Alfa; mayor proveedor de Gama'},
            {'source': 'Delta', 'target': 'Beta', 'w': 2, 'type': 'fab', 'rel': 'Compite en memoria'},
            {'source': 'Delta', 'target': 'Gama', 'w': 2, 'type': 'partner', 'rel': 'Delta usa Gama'},             # no flujo
            {'source': 'Beta', 'target': 'Gama', 'w': 5, 'type': 'owns', 'rel': 'Gama adquirió Beta en 2020'},     # al revés
            {'source': 'Alfa', 'target': 'Delta', 'w': 5, 'type': 'owns', 'rel': 'Alfa adquirió Delta en 2021'},   # correcto
            {'source': 'Beta', 'target': 'Delta', 'w': 2, 'type': 'supply', 'rel': 'Planta en USA para Delta'},    # "USA"
        ],
        'node_id_alias': {}, 'categories': {'fabless': {}}, 'sectors9': {'diseno': {}},
    }
    res = AG.audit_snapshot(snap)
    got = {(x['source'], x['target']): x['reason'] for x in res['findings']['text_direction']}
    assert got == {('Alfa', 'Beta'): 'subject_is_source', ('Gama', 'Alfa'): 'provider_of_source',
                   ('Delta', 'Beta'): 'rival_or_founder', ('Beta', 'Gama'): 'subject_is_target_buyer'}
    assert res['metrics']['text_direction'] == 4 and 'text_direction' in AG.RATCHET


# ── (c) escala de pesos ──────────────────────────────────────────────────────────────────────────────────────────
@needs_node
def test_c_pesos_conteos_y_reglas(snap, rv):
    links = snap['links']
    eq1 = sum(1 for l in links if float(l['w']) == 1)
    lt1 = sum(1 for l in links if float(l['w']) < 1)
    assert (eq1, lt1) == (462, 400) == (rv['counts']['weights_eq1'], rv['counts']['weights_lt1'])
    assert rv['counts']['weights_sole_lt1_flow'] == 41                     # BRECHAS L3-11
    cw = rv['c_weights']
    assert sum(cw['by_rule'].values()) == len(links)
    assert len(cw['items_w_le_1']) == eq1 + lt1
    crit = AG.load_vocab()['criticality']
    for x in cw['items_w_le_1']:
        if x['rule'] == 'scale_1_6':
            assert x['w01'] == round(float(x['w']) / 6, 4) and 'nodes/nodes_expand5.js' not in x['files']
        elif x['rule'] == 'placeholder':
            assert x['files'] == ['nodes/nodes_expand5.js']
            if x['placeholder_kind'] == 'criticality':
                assert abs(float(x['w']) - crit[x['type']]) < 1e-9
            else:                                    # PROP-14: el mismo número en todo el tipo (license 0,8 ×17)
                assert x['placeholder_kind'] == 'uniform_constant'
            assert 0 < x['w01'] <= 1
        elif x['rule'] == 'scale_0_1':
            assert x['w01'] == float(x['w'])
    uni = collections.Counter((x['type'], x['w']) for x in cw['items_w_le_1']
                              if x.get('placeholder_kind') == 'uniform_constant')
    assert uni == {('license', 0.8): 17}, uni                # BRECHAS PROP-14 "license 0.8 ×17"
    # el piso del proveedor único: w/6 ÷ max(Σ/6, 1) == w ÷ max(Σ, 6) → misma transmisión para los vínculos 1-6
    assert all(cw['per_type'][t]['n'] == sum(1 for l in links if l['type'] == t) for t in cw['per_type'])


# ── (d) verbos fuera de vocabulario y márgenes: lo MISMO que encuentran las puertas SHACL ────────────────────────
@needs_node
def test_d_coincide_con_las_puertas_shacl(snap, rv):
    from core.gates import engine
    from core.gates import focus as F
    comp = engine.compile_ir(engine.read_ir_file())

    def rules(triples):
        return {spec['rule'] for _t, _k, spec, _v, _l in engine.run(comp, triples)}

    off = set()
    for f in snap['temporal_facts']:
        if f.get('object_type') != 'node' or not f.get('rel'):
            continue
        tr, _ = F.link_triples({'id': f['id'], 'source': f['subject'], 'target': f['object'], 'rel': f['rel'],
                                'valid_from': f.get('valid_from')})
        if any(r.endswith('link.rel_in_vocab') for r in rules(tr)):
            off.add(f['id'])
    assert len(off) == 58 == rv['counts']['off_vocab_facts']
    assert {x['fact_id'] for x in rv['d_verbs']['facts']} == off
    bad = set()
    for n in snap['nodes']:
        tr, _ = F.object_triples({'id': n['id'], 'type': 'Company', 'props': {'margin': n.get('margin')}})
        if any(r.endswith('object.margin_range') for r in rules(tr)):
            bad.add(n['id'])
    assert len(bad) == 12 == rv['counts']['margins_out_of_range']
    assert {m['node'] for m in rv['d_verbs']['margins']} == bad
    env = {m['node']: m for m in rv['d_verbs']['margins']}
    assert env['Envicool']['proposal'] == {**env['Envicool']['proposal'], 'kind': 'percent_to_fraction', 'value': 0.2025}
    assert env['Rigetti']['proposal']['kind'] == 'keep_and_widen_rule' and env['Rigetti']['actions'] == []
    table = rv['d_verbs']['table']
    assert sum(r['n'] for r in table.values()) == 58
    assert {v for v, r in table.items() if r['question']} == {'controla', 'alberga', 'domina'}
    vocab = AG.load_vocab()['rel_types']
    for x in rv['d_verbs']['facts']:
        assert x['proposal']['type'] in vocab, x
    by = {x['fact_id']: x for x in rv['d_verbs']['facts']}
    compite = [x for x in by.values() if x['verb'] == 'compite']
    assert compite and all(not x['proposal']['flow'] for x in compite)
    # revisión: cada verbo migrado a Postgres trae la retracción DIRIGIDA de su vínculo con el verbo como rel_type
    # (canal migration_v0_temporal) y, si la propuesta relaciona (no 'about'), el ProponerVinculo con su fecha
    for x in rv['d_verbs']['facts']:
        acts = x['actions']
        assert acts and acts[0]['action'] == 'RetractarVinculo', x
        m = acts[0]['match']
        assert m['rel_type'] == x['verb'] and m['channel'] == 'migration_v0_temporal'
        assert (m['source'], m['target'], m['valid_from']) == (x['subject'], x['object'], x['valid_from'])
        p = x['proposal']
        if p['type'] == 'about':
            assert len(acts) == 1
        else:
            assert acts[1]['action'] == 'ProponerVinculo'
            assert (acts[1]['input']['from_id'], acts[1]['input']['to_id'], acts[1]['input']['tipo']) == (
                p['source'], p['target'], p['type'])


# ── (e) los más pesados sin fecha: ninguna fecha inventada ───────────────────────────────────────────────────────
@needs_node
def test_e_mas_pesados_sin_fecha(rv):
    h = rv['e_heaviest_undated']
    flow = AG.load_vocab()['flow']
    assert len(h) == 200 == rv['counts']['heaviest_undated']
    assert all(x['type'] in flow for x in h)
    assert all(x['proposed_since'] is None and x['source_url'] is None and x['mark'] is None for x in h)
    s = [x['strength'] for x in h]
    assert s == sorted(s, reverse=True)
    keys = {(x['source'], x['target'], x['type']) for x in h}
    assert len(keys) == 200
    dated = {(d['proposal'].get('source'), d['proposal'].get('target'), d['proposal'].get('type')): d['valid_from']
             for d in rv['a_dated_links']}
    for x in h:
        for hint in x['catalog_hint']:          # la pista es SOLO un hecho fechado de ESE mismo vínculo
            assert dated.get((x['source'], x['target'], x['type'])) == hint['valid_from']
    assert h[0]['source'] == 'TSMC' and h[0]['target'] == 'Nvidia' and h[0]['catalog_hint']


# ── el JSON no aplica nada; acciones del catálogo real ───────────────────────────────────────────────────────────
@needs_node
def test_json_pendiente_de_marcas_y_acciones_validas(rv):
    from ontology.actions import ACTION_CATALOG
    assert rv['apply']['status'] == 'pending_marks'
    items = rv['a_dated_links'] + rv['b_text_directions'] + rv['d_verbs']['facts'] + rv['d_verbs']['margins']
    assert all(it['mark'] is None for it in items)
    ids = [it['id'] for it in items + rv['e_heaviest_undated']]
    assert len(ids) == len(set(ids))
    acts = collections.Counter(a['action'] for it in items for a in it.get('actions') or ())
    assert set(acts) <= set(ACTION_CATALOG), acts
    assert acts['RetractarVinculo'] == 27 + 17 + 58


def test_el_script_no_escribe_en_la_base():
    src = open(os.path.join(ROOT, 'scripts', 'build_graph_review.py'), encoding='utf-8').read()
    for bad in ('apply_event', 'execute_action', 'apply_plan', 'rollback_run', 's.add(', 'session.add(', 'INSERT', 'UPDATE '):
        assert bad not in src, bad
    assert "SET TRANSACTION READ ONLY" in src


def test_resumen_de_reconciliacion():
    plan = {'as_of': '2026-10-13T00:00:00+00:00', 'snapshot': {'exported_at': 'x'}, 'out_of_scope': {'fecha_real': 81},
            'summary': {'alias': 3, 'duplicates': 2, 'direction': 5, 'variants': 1, 'missing': 0, 'extra': 7,
                        'objects_missing': 4, 'missing_rejected': 0, 'db_links_vigentes': 3042, 'db_objects': 1294,
                        'catalog_links': 2510, 'catalog_nodes': 937}}
    txt = '\n'.join(GR.reconcile_summary(plan))
    assert '1294 objetos' in txt and '3042 vínculos vigentes' in txt and 'fecha_real 81' in txt
    assert 'direction' in txt and 'tu marca' in txt


def test_db_sin_database_url(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    assert 'DATABASE_URL' in GR.live_reconcile()[0]


@pytest.mark.skipif(not os.getenv('DATABASE_URL'), reason='sin DATABASE_URL')
def test_db_plan_en_vivo_es_solo_lectura():
    from sqlalchemy import text

    from ontology.db import init_schema, session_scope
    init_schema()
    with session_scope() as s:
        before = s.execute(text('SELECT count(*) FROM events')).scalar()
    lines = GR.live_reconcile()
    assert lines[0].startswith('Plan de reconciliación')
    with session_scope() as s:
        assert s.execute(text('SELECT count(*) FROM events')).scalar() == before


@needs_node
def test_md_cifras_del_relato_salen_de_los_conteos(rv):
    """Revisión: el relato de (c) y (d) no lleva números escritos a mano (se quedaban viejos con --check verde)."""
    md = GR.render_md(rv)
    c = rv['counts']
    assert f'{c["weights_sole_lt1_flow"]} de ellos son el ÚNICO proveedor' in md
    assert f'Resultado: {c["weights_lt1"]} vínculos' in md and 'unos 400' not in md
    nq = sum(1 for r in rv['d_verbs']['table'].values() if r['question'])
    assert f'las {nq} con "?"' in md
    assert 'del DUEÑO a lo que posee' in md                  # (b) owns: el comprador quedó como destino
    assert 'MISMO número en todo su tipo' in md and 'license' in md
