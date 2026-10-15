"""tests/test_import_lote2.py — lote L (2026-10-15): las 386 fichas COMPLETAS de la entrega P1.

  · `scripts/import_companies.py --lote2 --check`: el paquete saneado y el registro del repositorio son los que se
    generarían hoy; las 386 validan; ninguna de las 9 excluidas entra; el archivo de fichas es el de la entrega (sha);
  · `load_bundle` lee `.gz`; el plan con `sanitize=True` sobre las fichas ORIGINALES da la MISMA huella que el paquete
    saneado (el saneador es idempotente de punta a punta);
  · identidad: las 14 fichas que la entrega marca «fusionar» se fusionan con su empresa (Boeing, RTX→Raytheon, BAM→
    Brookfield, Samsung, Foxconn, Ørsted→Orsted…); las especiales NO (Moody's ≠ Moody's Ratings, S&P Global ≠ S&P Global
    Ratings, Brookfield Renewable, TSMC Arizona, SoftBank Vision Fund; MOL Hungría ≠ MOL; SoftBank Corp. ≠ SoftBank
    Group); un identificador FUERTE gana a la pista y el conflicto se LISTA;
  · vínculos: el id viejo de la contraparte (`id_hint`: lockheed-martin) resuelve; owns sin dependency lleva
    `criticality_source: default_owns` y solo entra vivo con un % de control declarado; partner/invest sin dependency
    pesan 1; participaciones sin % nunca entran vivas;
  · el plan es estable (dos corridas = misma huella) y coincide con docs/expansion/LOTE_2026-10-15_PLAN.md cuando el
    grafo es el mismo."""
import copy
import gzip
import hashlib
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('KHIPU_SCHEDULER', 'off')

from ontology import company_import as CI  # noqa: E402

LOTE = os.path.join(ROOT, 'data', 'import', 'lotes', '2026-10-15')
DOC = os.path.join(ROOT, 'docs', 'expansion', 'LOTE_2026-10-15_PLAN.md')
FUSIONES = {   # 1d_crosswalk_csv_a_ids.csv (fusionar_con_existente = true) ∩ las 386 completas
    'fb-2026-boeing': 'Boeing', 'fb-2026-rtx': 'Raytheon', 'fb-2026-brookfield-asset-management': 'Brookfield',
    'fb-2026-prysmian': 'Prysmian', 'fb-2026-samsung-electronics': 'Samsung', 'fb-2026-foxconn': 'Foxconn',
    'fb-2026-dhl-group': 'DHL_Group', 'fb-2026-ge-aerospace': 'GE_Aerospace', 'fb-2026-ericsson': 'Ericsson',
    'fb-2026-shell': 'Shell', 'fb-2026-kazatomprom': 'Kazatomprom', 'fb-2026-rsted': 'Orsted',
    'fb-2026-montage-technology': 'Montage', 'fb-2026-maersk': 'Maersk',
}
NO_FUSIONAR = {   # 3_fusionar_con_existentes.csv / README: parecidas pero OTRAS empresas
    'fb-2026-moody-s': 'MoodysRatings', 'fb-2026-s-p-global': 'SPGlobalRatings',
    'fb-2026-brookfield-renewable': 'Brookfield', 'fb-2026-tsmc-arizona': 'TSMC',
    'fb-2026-softbank-vision-fund': 'SoftBank',
}


@pytest.fixture(scope='module')
def view():
    """El grafo de los lectores desde el SNAPSHOT (sin base), como lo ve la terminal sin DATABASE_URL."""
    import ontology.db as odb
    from core.hotviews import hot, registry
    real = odb.ontology_available
    odb.ontology_available = lambda: False
    try:
        registry.reset()
        hot.reset()
        v = hot.graph()
    finally:
        odb.ontology_available = real
    assert v is not None and len(v.nodes) >= 900
    return v


@pytest.fixture(scope='module')
def bundle():
    return CI.load_bundle(os.path.join(LOTE, CI.LOTE2_BUNDLE))


@pytest.fixture(scope='module')
def lote_plan(bundle, view):
    return CI.plan(bundle['records'], bundle['updates'], view=view, batch=bundle['batch'], what_changes=True)


# ── el paquete del repositorio ──────────────────────────────────────────────────────────────────────────────────
def test_check_del_paquete_y_el_registro(capsys):
    from scripts import import_companies as IC
    assert IC.main(['--lote2', '--check']) == 0
    assert '✓' in capsys.readouterr().out


def test_solo_las_386_completas_y_ninguna_excluida(bundle):
    ids = CI.complete_record_ids()
    assert len(ids) == len(set(ids)) == 386
    recs = bundle['records']
    assert [r['record_id'] for r in recs] and {r['record_id'] for r in recs} == set(ids)
    excl = {r['record_id'] for r in CI._read_csv(os.path.join(LOTE, 'fichas_excluidas.csv'))}
    assert len(excl) == 9 and not excl & set(ids)
    valid, invalid = CI.validate_batch(recs)
    assert len(valid) == 386 and invalid == []
    assert bundle['batch'] == CI.LOTE2_BATCH and bundle['updates'] == [] and bundle['approve_categories'] == []


def test_origen_las_lineas_son_las_de_la_entrega():
    with open(os.path.join(LOTE, 'ORIGEN.json'), encoding='utf-8') as fh:
        origin = json.load(fh)
    with gzip.open(os.path.join(LOTE, CI.LOTE2_FICHAS), 'rb') as fh:
        raw = fh.read()
    assert hashlib.sha256(raw).hexdigest() == origin['kept_lines_sha256']
    assert origin['kept_records'] == 386 and origin['package_records'] == 395 and len(origin['excluded']) == 9


def test_registro_del_saneador(bundle):
    with open(os.path.join(LOTE, CI.LOTE2_LOG), encoding='utf-8') as fh:
        log = json.load(fh)
    assert log['schema'] == CI.SANITIZE_LOG_SCHEMA and log['records_in'] == 386
    s = log['summary']
    assert s['fields_dropped'] == 6 and s['rejected'] == [] and s['fields_repaired'] >= 1600
    assert sum(len(v) for v in log['records'].values()) == sum(s['by_rule'].values())
    assert set(log['records']) <= {r['record_id'] for r in bundle['records']}


def test_load_bundle_lee_gz_y_jsonl_gz(tmp_path):
    b = CI.load_bundle(os.path.join(LOTE, CI.LOTE2_BUNDLE))
    assert len(b['records']) == 386
    raw = CI.load_bundle(os.path.join(LOTE, CI.LOTE2_FICHAS))          # .jsonl.gz → una ficha por línea
    assert len(raw['records']) == 386 and raw['records'][0]['schema'] == 'khipus.company/1'
    p = tmp_path / 'uno.json.gz'
    p.write_bytes(gzip.compress(json.dumps([b['records'][0]]).encode('utf-8')))
    assert CI.load_bundle(str(p))['records'][0]['record_id'] == b['records'][0]['record_id']


# ── identidad ───────────────────────────────────────────────────────────────────────────────────────────────────
def test_las_14_fusiones_de_la_entrega(lote_plan):
    by = {it['record_id']: it for it in lote_plan['items']}
    for rid, existing in FUSIONES.items():
        assert by[rid]['action'] == 'merge' and by[rid]['id'] == existing, (rid, by[rid]['action'], by[rid]['id'])
    merged = {it['record_id'] for it in lote_plan['items'] if it['action'] == 'merge'}
    assert merged == set(FUSIONES)


def test_las_especiales_no_se_fusionan(lote_plan):
    by = {it['record_id']: it for it in lote_plan['items']}
    for rid, not_this in NO_FUSIONAR.items():
        assert by[rid]['action'] == 'create' and by[rid]['id'] != not_this, (rid, by[rid]['id'])
    for rid in ('fb-2026-moody-s', 'fb-2026-s-p-global'):
        assert any(c['kind'] == 'name_target_is_counterparty' for c in by[rid]['conflicts'])
    # la filial queda como OTRA empresa: Moody's es dueño de Moody's Ratings (no un vínculo consigo mismo)
    mo = by['fb-2026-moody-s']
    assert by['fb-2026-moody-s']['id'] == 'MoodyS'
    assert any(l.get('target') == 'MoodysRatings' or l.get('source') == 'MoodysRatings' for l in mo['links'])
    assert not any(l.get('reason') == 'self_link' for it in lote_plan['items'] for l in it['links'])


def _synth(rid, name, hq, yahoo, hint, mic, legal=None, isin=None):
    F = {'source_url': 'https://ex.com/s', 'source_kind': 'corporate', 'as_of': '2026-10', 'confidence': 0.9}
    ids = {'yahoo_symbol': yahoo, **({'isin': [isin]} if isin else {})}
    return {'schema': 'khipus.company/1', 'record_id': rid, 'khipus_id_hint': hint,
            'research_meta': {'researcher': 't', 'researched_at': '2026-10-15T00:00:00Z', 'method': 'manual', 'tier': 'A'},
            'identity': {'legal_name': {'value': legal or name, **F}, 'short_name': name, 'status': {'value': 'public', **F},
                         'hq_country': {'value': hq, **F}, 'ids': ids},
            'listings': [{'ticker': yahoo.split('.')[0], 'exchange_mic': mic, 'yahoo_symbol': yahoo, 'currency': 'HUF'
                          if hq == 'HU' else 'JPY', 'kind': 'equity', 'is_primary': True, 'source_url': 'https://ex.com/l',
                          'as_of': '2026'}],
            'classification': {'cat': 'foundry'},
            'profile': {'summary': {'value': 'Empresa de prueba larga', 'value_en': 'Test company long enough', **F}}}


def test_mol_hungria_y_softbank_corp_no_se_fusionan(view):
    recs = [_synth('t-mol', 'MOL', 'HU', 'MOL.BD', 'MOLGroup', 'XBUD', 'MOL Hungarian Oil & Gas Plc', 'HU0000153937'),
            _synth('t-mol-hint', 'MOL', 'HU', 'MOL.BD', 'MOL', 'XBUD', 'MOL Hungarian Oil & Gas Plc'),   # pista = la japonesa
            _synth('t-sbc', 'SoftBank Corp.', 'JP', '9434.T', 'SoftBankCorp', 'XTKS')]
    p = CI.plan(recs, [], view=view, batch='t', what_changes=False)
    by = {it['record_id']: it for it in p['items']}
    assert by['t-mol']['action'] == 'create' and by['t-mol']['id'] == 'MOLGroup'
    assert by['t-mol-hint']['action'] == 'create' and by['t-mol-hint']['id'] != 'MOL'
    assert any(c['kind'] == 'country_mismatch' and c['id'] == 'MOL' for c in by['t-mol-hint']['conflicts'])
    assert by['t-sbc']['action'] == 'create' and by['t-sbc']['id'] != 'SoftBank'


def test_identificador_fuerte_gana_a_la_pista_y_se_lista(view):
    r = _synth('t-strong', 'Algo Distinto', 'US', 'BA', 'Raytheon', 'XNYS')    # Yahoo = Boeing, pista = Raytheon
    r['listings'][0]['currency'] = 'USD'
    p = CI.plan([r], [], view=view, batch='t', what_changes=False)
    it = p['items'][0]
    assert it['action'] == 'merge' and it['id'] == 'Boeing' and it['method'] == 'yahoo_symbol'
    assert {'kind': 'hint_mismatch', 'hint': 'Raytheon', 'resolved': 'Boeing'} in it['conflicts']


def test_la_pista_existente_gana_al_parecido_de_nombre(view):
    r = _synth('t-hint', 'Boeing', 'US', 'X.L', 'Raytheon', 'XLON')       # el NOMBRE dice Boeing, la pista Raytheon
    r['identity']['ids'] = {}
    r.pop('listings')
    p = CI.plan([r], [], view=view, batch='t', what_changes=False)
    it = p['items'][0]
    assert it['action'] == 'merge' and it['id'] == 'Raytheon' and it['method'] == 'hint'
    assert any(c['kind'] == 'name_differs_from_hint' and c['id'] == 'Boeing' for c in it['conflicts'])


# ── vínculos ────────────────────────────────────────────────────────────────────────────────────────────────────
def _links(lote_plan, rid):
    return next(it for it in lote_plan['items'] if it['record_id'] == rid)['links']


def test_id_viejo_de_la_contraparte_resuelve(lote_plan):
    nasa = _links(lote_plan, 'fb-2026-nasa')
    lm = [l for l in nasa if l['counterparty'].get('id') == 'lockheed-martin']
    assert lm and lm[0]['counterparty']['how'] == 'khipus_id'


def test_owns_sin_dependency_y_participaciones_sin_porcentaje(lote_plan, view):
    pol = CI.policy()
    owns_def = [l for it in lote_plan['items'] for l in it['links']
                if (l.get('properties') or {}).get('criticality_source') == 'default_owns']
    assert owns_def
    for l in owns_def:
        props = l['properties']
        assert l['rel_type'] == 'owns' and l['weight'] == float(props['criticality'])
        assert props['criticality'] == CI._owns_default_criticality(props.get('criticality_pct'), pol)
        if l['route'] == 'live':
            assert props.get('criticality_pct', 0) >= pol['owns_default_live_min_pct']
    ndf = _links(lote_plan, 'fb-2026-national-development-fund-taiwan')
    tsmc = [l for l in ndf if l.get('target') == 'TSMC' and l['rel_type'] == 'owns']
    assert tsmc and tsmc[0]['route'] == 'proposed' and tsmc[0]['reason'] == 'owns_without_control_pct'   # 6,38 % ≠ control
    nonflow = [l for it in lote_plan['items'] for l in it['links']
               if (l.get('properties') or {}).get('criticality_source') == 'default_nonflow']
    assert nonflow and all(l['rel_type'] in ('partner', 'invest') and l['weight'] == 1.0 for l in nonflow)
    no_pct = [l for it in lote_plan['items'] for l in it['links']
              if (l.get('properties') or {}).get('share_pct_known') is False]
    assert no_pct and all(l['route'] in ('proposed', 'pending') for l in no_pct)


def test_sin_dependency_el_peso_de_flujo_sigue_siendo_la_criticidad(lote_plan):
    for it in lote_plan['items']:
        for l in it['links']:
            dep = (l.get('properties') or {}).get('dependency') or {}
            if l['rel_type'] in ('supply', 'fab', 'cloud', 'license', 'ppa', 'deploy') and l.get('weight') is not None:
                assert l['weight'] == float(dep['criticality'])


# ── el plan ─────────────────────────────────────────────────────────────────────────────────────────────────────
def test_plan_estable_y_saneador_de_punta_a_punta(bundle, view, lote_plan):
    p2 = CI.plan(bundle['records'], [], view=view, batch=bundle['batch'], what_changes=False)
    assert p2['plan_sha'] == lote_plan['plan_sha'] and p2['counts'] == lote_plan['counts']
    with gzip.open(os.path.join(LOTE, CI.LOTE2_FICHAS), 'rt', encoding='utf-8') as fh:
        raw = [json.loads(ln) for ln in fh.read().splitlines() if ln.strip()]
    p3 = CI.plan(copy.deepcopy(raw), [], view=view, batch=bundle['batch'], what_changes=False, sanitize=True)
    assert p3['plan_sha'] == lote_plan['plan_sha']
    assert p3['sanitize']['fields_dropped'] == 6 and p3['sanitize']['rejected'] == []
    p4 = CI.plan(copy.deepcopy(raw), [], view=view, batch=bundle['batch'], what_changes=False)    # sin sanear
    assert p4['counts']['valid'] < 386                                          # sin sanear, faltan (99 de 386 hoy)


def test_numeros_del_plan(lote_plan):
    c = lote_plan['counts']
    assert c['records'] == c['valid'] == 386 and c['invalid'] == 0 and c['skip'] == 0
    assert c['merge'] == 14 and c['create'] == 372 and c['categories_to_approve'] == 0
    assert sum(c['links'].values()) == sum(len(it['links']) for it in lote_plan['items'])
    wc = lote_plan['what_changes']
    assert wc['available'] and wc['calibration_stale'] and wc['added_nodes'] == 372
    top_after = [x['id'] for x in wc['after']['chokepoints']]
    assert top_after[0] == 'TSMC' and 'NationalDevelopmentFund' not in top_after   # un 6 % no es un cuello de botella


def test_el_documento_dice_los_numeros_del_plan(lote_plan):
    with open(DOC, encoding='utf-8') as fh:
        doc = fh.read()
    m = re.search(r'Huella del plan en ESTA PC: `([0-9a-f]{64})` \(grafo `([^`]+)`\)', doc)
    assert m, 'el documento no trae la huella'
    if m.group(2) != lote_plan['graph_key']:
        pytest.skip(f'el catálogo cambió desde que se escribió el documento ({m.group(2)} ≠ {lote_plan["graph_key"]}): '
                    'regenerar con scripts/import_companies.py --lote2 --md docs/expansion/LOTE_2026-10-15_PLAN.md')
    assert m.group(1) == lote_plan['plan_sha']
    c = lote_plan['counts']
    assert f'Se crean **{c["create"]}**' in doc and f'se fusionan con una que ya existe **{c["merge"]}**' in doc
    assert '14' in doc and 'Moody' in doc and 'Las 9 fichas que NO entran' in doc
