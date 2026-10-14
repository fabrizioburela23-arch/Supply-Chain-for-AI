"""tests/test_lotek_fixer.py — revisión del lote K (2026-10-14): lo que el revisor encontró y el integrador arregló.

Sin base: guardián de cifras del chat (comas decimales dentro de paréntesis), abreviaturas de estados de EE.UU. en
place_country, ids khipus con Ø/Æ/ß, listados secundarios que resuelven (TOELY → TEL), regla de cotización principal
(Siemens «Sp. ADRs» en Stuttgart), sufijo «(GDR)» del nombre, ISIN del CEDEAR fuera de los ids, guardia del orden
compuesto de Impact (pct > 100 → lexsort), ReconcileError = rechazo, alias de categoría del catálogo.
Con base (DATABASE_URL): el grafo que cambió SIN reconstruir la vista → graph_changed; aplicar → deshacer → aplicar
revive la empresa retirada; un pendiente resuelto no se vuelve a escribir (ni revive al deshacer) y se empareja con la
contraparte que llega en el MISMO lote; trozo zlib «bomba» → 413.
"""
import base64
import json
import os
import sys
import zlib

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('KHIPU_SCHEDULER', 'off')

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


# ── sin base ────────────────────────────────────────────────────────────────────────────────────────────────────
def test_quitar_nombres_de_herramientas_no_rompe_cifras():
    from core.khipu_chat import strip_tool_names
    facts = [{'kind': 'get_company', 'source': 'khipus:graph'}]
    assert strip_tool_names('Nvidia cotiza a 182,40 USD (get_company, +1,36 % hoy, Yahoo).', facts, 'es') == \
        'Nvidia cotiza a 182,40 USD (Grafo Khipus, +1,36 % hoy, Yahoo).'
    assert strip_tool_names('Subió (get_company) un 2,5 % (233,95 USD, Yahoo, hoy).', facts, 'es') == \
        'Subió (Grafo Khipus) un 2,5 % (233,95 USD, Yahoo, hoy).'
    assert strip_tool_names('Cap (130,497,000,000 USD) per get_company.', facts, 'en') == 'Cap (130,497,000,000 USD) per Khipus graph.'
    # el paréntesis que recibió el reemplazo SÍ se deduplica; los demás quedan intactos
    assert strip_tool_names('Fuente (get_company, Grafo Khipus, hoy) y (1,2 % promedio).', facts, 'es') == \
        'Fuente (Grafo Khipus, hoy) y (1,2 % promedio).'


def test_estados_de_eeuu_en_textos_de_lugar():
    from core.world import place_country
    assert place_country('Boulder, CO') == 'EEUU' and place_country('Chicago, IL') == 'EEUU'
    assert place_country('Dover, DE') == 'EEUU' and place_country('Madrid, ES') == 'EEUU' or place_country('Madrid, ES') == 'Espana'
    assert place_country('Ridgecrest, CA') == 'EEUU' and place_country('Berlin, Germany') == 'Alemania'
    assert place_country('Bogotá, Colombia') == 'Colombia'


def test_khipus_id_con_letras_latinas_especiales():
    from core.import_normalize import khipus_id_from
    assert khipus_id_from('Ørsted') == 'Orsted' and khipus_id_from('Łódź Ltd') == 'LodzLtd'
    assert khipus_id_from('Straße AG') == 'StrasseAG' and khipus_id_from('Ægir') == 'AEgir'
    assert khipus_id_from('LG Energy Solution') == 'LGEnergySolution'


def test_listados_secundarios_resuelven_por_ticker():
    from core import entities
    r = entities.resolve('TOELY')
    assert r and r['id'] == 'TEL' and r['method'] == 'ticker'
    assert entities.resolve('8035.T')['id'] == 'TEL'
    assert entities.resolve('AJINY')['id'] == 'Ajinomoto' and entities.resolve('SMNEY')['id'] == 'SiemensEnergy'
    assert 'TEL' in entities.search_scores('TOELY')


def test_regla_de_cotizacion_principal_con_certificados_en_la_sede():
    from ontology import company_import as CI
    assert CI._primary_rule('XSTU', 'DE', 'US8261975010', legal_name='SIEMENS AG Shares (Sp. ADRs)/1/') == (False, 'primary_is_depositary')
    assert CI._primary_rule('XSTU', 'DE', 'DE000A3H3LL2', legal_name='Vantage Towers AG') == (True, None)
    assert CI._primary_rule('XETR', 'DE', 'US8261975010', legal_name='Siemens AG (ADR)') == (True, None)
    assert CI._primary_rule('XBUE', 'US', 'ARDEUT110061') == (False, 'primary_is_depositary')
    assert CI._primary_rule('OTCM', 'US', 'US0378331005', legal_name='Apple Inc.') == (True, None)
    assert CI._strip_depositary_suffix('Samsung Electronics (GDR)') == ('Samsung Electronics', 'GDR')
    assert CI._strip_depositary_suffix('Intek (KME)') == ('Intek (KME)', None)


def test_adaptador_lote1_siemens_samsung_boeing():
    from ontology import company_import as CI
    b = CI.adapt_lote_2026_10_14()
    by = {r['identity']['short_name']: r for r in b['records']}
    sie = by['Siemens']
    assert sie['listings'][0]['is_primary'] is False and 'isin' not in (sie['identity'].get('ids') or {})
    assert sie['listings'][0]['isin'] == 'US8261975010'               # el ISIN del certificado vive SOLO en la cotización
    boe = by['Boeing']
    assert boe['listings'][0]['exchange_mic'] == 'XBUE' and 'isin' not in boe['identity'].get('ids', {}) and 'figi' not in boe['identity'].get('ids', {})
    sam = by['Samsung Electronics']
    assert sam['identity']['other_names'] == [{'name': 'Samsung Electronics (GDR)', 'kind': 'common'}]
    assert any(w['code'] == 'depositary_name' and w['name'] == 'Samsung Electronics' for w in b['warnings'])
    assert 'Samsung Electronics (GDR)' not in by


def test_plan_sobre_el_catalogo_samsung_fusiona_y_orsted_no_duplica():
    from core.hotviews import hot
    from ontology import company_import as CI
    v = hot.graph()
    b = CI.adapt_lote_2026_10_14()
    recs = [r for r in b['records'] if r['identity']['short_name'] in ('Samsung Electronics', 'Ørsted', 'Siemens', 'ElringKlinger')]
    p = CI.plan(recs, [], view=v, batch='k', what_changes=False)
    by = {it['name']: it for it in p['items']}
    assert by['Samsung Electronics']['action'] == 'merge' and by['Samsung Electronics']['id'] == 'Samsung'
    assert by['Ørsted']['action'] == 'merge' and by['Ørsted']['id'] == 'Orsted'
    sie = by['Siemens']
    assert sie['action'] == 'create' and not sie['props'].get('mkt')
    assert any(c['kind'] == 'possible_duplicate' and c.get('method') == 'only_depositary_listing' for c in sie['conflicts'])
    # alias del catálogo: battery_components (fusionada) → battery_cells, sin categoría por aprobar
    assert by['ElringKlinger']['props']['cat'] == 'battery_cells' and by['ElringKlinger']['props'].get('cat_declared') == 'battery_components'
    assert p['counts']['categories_to_approve'] == 0


def test_orden_compuesto_cae_a_lexsort_si_un_pct_pasa_de_100():
    import random

    import numpy as np

    from core.hotviews.views import impact
    rng = random.Random(3)
    n, m = 50, 400
    src = np.asarray(sorted(rng.randrange(8) for _ in range(m)), dtype=np.int64)
    pct = np.asarray([round(rng.random() * 100, 2) for _ in range(m)])
    pct[m // 2] = 100.5                                      # en una fuente que no es la primera
    hop = np.asarray([rng.randrange(4) for _ in range(m)], dtype=np.int64)
    rank = np.asarray([rng.randrange(n) for _ in range(m)], dtype=np.int64)
    assert impact._orden(src, pct, hop, rank, n).tolist() == np.lexsort((rank, hop, -pct, src)).tolist()


def test_reconcile_error_es_rechazo_no_fallo():
    from ontology import company_import as CI
    from ontology.reconcile import ReconcileError
    assert CI._rej_status(ReconcileError('x')) == 'rejected' and CI._rej_status(RuntimeError('x')) == 'failed'
    assert CI._rej_status(CI.ImportProblem('x', code='busy')) == 'rejected'
    assert CI._busy_import().code == 'busy'


def test_mcp_get_company_expone_market_position_y_contrato():
    from mcp_server import contract
    r = {'id': 'CATL', 'label': 'CATL', 'market_position': [{'market': 'baterías', 'share_pct': 37}] * 7, 'top_suppliers': [], 'top_customers': []}
    out = contract.SUMMARIZERS['get_company'](r)
    assert len(out['market_position']) == 5
    src = open(os.path.join(ROOT, 'mcp_server', 'tools.py'), encoding='utf-8').read()
    assert "out['market_position'] = list(cc.get('market_position') or [])" in src


def test_categorias_nuevas_distinguibles_de_todas():
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))
    import build_categories as B
    doc = B.load()
    for t in ('light', 'dark'):
        assert B.min_delta_e(doc, t)[0] >= 10
    assert B.delta_e('#884511', '#8A4410') < 5 and B.delta_e('#000000', '#FFFFFF') > 99


def test_cli_plan_en_el_servidor_documentado():
    src = open(os.path.join(ROOT, 'scripts', 'import_companies.py'), encoding='utf-8').read()
    assert 'if a.plan and a.server:' in src and "'/api/ontology/import/plan'" in src
    assert '--plan lote1.json --server' in src


def test_genui_filas_y_columnas_compactas_y_suscripcion_en_vivo():
    ch = open(os.path.join(ROOT, 'engine', 'genui_charts.js'), encoding='utf-8').read()
    assert "fmt(v, unit.unit, { currency: unit.currency, compact: true })" in ch
    assert 'max-height:calc(100% - 36px)' in ch and 'minmax(54px,auto)' in ch
    ow = open(os.path.join(ROOT, 'engine', 'oswindows.js'), encoding='utf-8').read()
    assert "window.addEventListener('khipu:hotquote', hqRepaint)" in ow and 'HQ.subs' in ow
    g = open(os.path.join(ROOT, 'engine', 'genui.js'), encoding='utf-8').read()
    assert "el: tl, put:" in g and "compact: k[0] === 'market_cap'" in g
    tg = open(os.path.join(ROOT, 'engine', 'temporal-graph.js'), encoding='utf-8').read()
    assert "L('Exposición de tu portafolio', 'Your portfolio exposure')" in tg and 'Depends (hidden) on:' in tg


def test_corrida_diaria_salta_secundarios_dados_de_baja(monkeypatch):
    """prices_store._targets: un listado secundario cuya nota dice «dado de baja» no se baja a diario; a pedido sí."""
    from core import instruments, prices_store
    monkeypatch.setattr(instruments, 'seed', lambda session, nodes=None: None)
    rows = [('8035.T', 'equity', 'JPY', {'primary': '8035.T'}, True),
            ('TOELY', 'adr', 'USD', {'primary': '8035.T', 'note': 'ADR OTC: el agregador lo marca dado de baja; verificar'}, False),
            ('2330.TW', 'equity', 'TWD', {'primary': 'TSM', 'note': 'cotización local (home)'}, False),
            ('SPY', 'etf', 'USD', None, True), ('JPY', 'fx', 'USD', {'ccy': 'JPY'}, True)]

    class _S:
        def execute(self, *_a, **_k):
            class _R:
                def all(self_inner):
                    return rows
            return _R()
    eq, fx = prices_store._targets(_S())
    assert eq == ['SPY', '8035.T', '2330.TW'] and fx == ['JPY']
    eq2, _ = prices_store._targets(_S(), symbols=['toely'])
    assert eq2 == ['TOELY']


# ── con base ────────────────────────────────────────────────────────────────────────────────────────────────────
from tests.test_import_roundtrip import PIN, H, _dbname, _principal, _rebuild, _synth, bundle, client, db  # noqa: E402,F401


def _plan_apply(recs, view=None, batch='k'):
    from ontology import company_import as CI
    from ontology.db import session_scope
    view = view or _rebuild()
    p = CI.plan(recs, [], view=view, batch=batch, what_changes=False)
    return p, CI.apply_run(session_scope, p, _principal(), confirm_db=_dbname(), expect={'plan_sha': p['plan_sha']}, view=view)


@needs_db
def test_grafo_cambiado_sin_reconstruir_la_vista_da_graph_changed(db):
    from ontology import company_import as CI
    from ontology.db import session_scope
    from ontology.service import apply_event
    v = _rebuild()
    h1 = _synth('t-h1', 'H1Cells', 'H1 Cells')
    h1['listings'][0].update(ticker='000011', yahoo_symbol='000011.KS')
    p = CI.plan([h1], [], view=v, batch='h1', what_changes=False)
    with session_scope() as s:      # una escritura confirmada entre plan y apply: la vista NO se reconstruye
        apply_event(s, 'ObjectCreated', {'label': 'H1 Cells', 'type': 'Company', 'properties': {'role': 'curado a mano'}},
                    valid_from='2020-01-01', source='pytest', actor='pytest', object_id='H1Cells')
    with pytest.raises(CI.ImportProblem) as e:
        CI.apply_run(session_scope, p, _principal(), confirm_db=_dbname(), expect={'plan_sha': p['plan_sha']}, view=v)
    assert e.value.code == 'graph_changed'
    with session_scope() as s:
        from ontology.models import ObjectRecord
        assert s.get(ObjectRecord, 'H1Cells').properties['role'] == 'curado a mano'     # nada pisado


@needs_db
def test_aplicar_deshacer_aplicar_revive_la_empresa(db):
    from ontology import company_import as CI
    from ontology.db import session_scope
    from ontology.models import ObjectRecord
    rec = _synth('t-h4', 'H4Cells', 'H4 Cells')
    rec['relations'] = []
    rec['listings'][0].update(ticker='000004', yahoo_symbol='000004.KS')
    p, res = _plan_apply([rec])
    assert res['objects_created'] >= 1 and res['objects_revived'] == 0        # (+ sus objetos Source)
    with session_scope() as s:
        CI.rollback_run(s, res['run_id'], _principal(), confirm_db=_dbname())
    v = _rebuild()
    assert 'H4Cells' not in v.by_id
    p2, res2 = _plan_apply([rec], view=v)
    assert p2['items'][0]['action'] == 'create'
    assert res2['objects_revived'] == 1 and res2['objects_created'] >= 1
    with session_scope() as s:
        pr = s.get(ObjectRecord, 'H4Cells').properties
        assert pr['retired'] is False and pr['merged_into'] is None and pr['rollback_run'] is None
        assert [r for r in CI.list_runs(s) if r['run_id'] == res2['run_id']][0]['summary']['objects_revived'] == 1
    assert 'H4Cells' in _rebuild().by_id


@needs_db
def test_pendiente_se_consume_una_vez_y_se_empareja_con_el_lote(db):
    from ontology import company_import as CI
    from ontology.db import session_scope
    a = _synth('t-h3a', 'H3Alpha', 'H3 Alpha')
    a['relations'] = [a['relations'][3]]                       # solo la contraparte desconocida → pendiente
    a['relations'][0]['counterparty'] = {'name': 'H3 Beta Pendiente'}
    p1, r1 = _plan_apply([a])
    assert r1['pending'] == 1 and r1['links_created'] == 0
    with session_scope() as s:
        assert len(CI.pending_links(s)) == 1
    # la contraparte llega en el lote siguiente: se empareja por NOMBRE dentro del mismo lote (antes hacía falta otra corrida)
    b = _synth('t-h3b', 'H3Beta', 'H3 Beta Pendiente')
    b['relations'] = []
    b['listings'][0].update(ticker='000002', yahoo_symbol='000002.KS')     # otra acción (si no, fusionaría con H3Alpha)
    v = _rebuild()
    with session_scope() as s:
        pend = CI.pending_links(s)
    p2 = CI.plan([b], [], view=v, batch='k', pending=pend, what_changes=False)
    pr = p2['pending_resolved']
    assert len(pr) == 1 and pr[0]['source'] == 'H3Beta' and pr[0]['target'] == 'H3Alpha'   # Alpha era el CLIENTE
    r2 = CI.apply_run(session_scope, p2, _principal(), confirm_db=_dbname(), expect={'plan_sha': p2['plan_sha']}, view=v)
    assert r2['links_created'] == 1
    # consumido: ya no vuelve a planearse ni a escribirse
    v = _rebuild()
    with session_scope() as s:
        assert CI.pending_links(s) == [] and len(CI.pending_links(s, include_consumed=True)) == 1
        pend = CI.pending_links(s)
    p3 = CI.plan([], [], view=v, batch='k', pending=pend, what_changes=False)
    assert p3['pending_resolved'] == [] and p3['counts']['events_estimated'] == 0
    # deshacer la corrida que lo resolvió retracta el vínculo pero NO revive el pendiente (decisión explícita)
    with session_scope() as s:
        CI.rollback_run(s, r2['run_id'], _principal(), confirm_db=_dbname())
    with session_scope() as s:
        assert CI.pending_links(s) == []


@needs_db
def test_trozo_zlib_bomba_da_413(client):
    from ontology import company_import as CI
    limit = int(CI.policy('upload_chunk_max_bytes'))
    bomb = zlib.compress(b'0' * (limit * 4), 9)
    assert len(bomb) < limit // 100
    r = client.post('/api/ontology/import/files', json={'name': 'x.json', 'sha256': 'c' * 64, 'chunk': 0, 'chunks': 1,
                                                          'data': base64.b64encode(bomb).decode('ascii'), 'encoding': 'zlib'}, headers=H)
    assert r.status_code == 413 and r.get_json()['code'] == 'chunk_too_big'


@needs_db
def test_importador_delega_en_el_resolvedor_unico(db):
    """Con la vista vigente, company_import.resolve_ids ES core.entities.resolve_ids (HKEX con ceros, ambiguos)."""
    from core import entities
    from ontology import company_import as CI
    v = _rebuild()
    mine = CI.resolve_ids({'ticker': '981', 'mic': 'XHKG'}, view=v)
    ref = entities.resolve_ids({'ticker': '981', 'mic': 'XHKG'})
    assert mine == ref and (ref or {}).get('id') == 'SMIC'
    calls = []
    orig = entities.resolve_ids
    entities.resolve_ids = lambda ids, name=None: calls.append(1) or orig(ids, name)
    try:
        CI.plan([_synth('t-dlg', 'DlgCells', 'Dlg Cells')], [], view=v, batch='k', what_changes=False)
    finally:
        entities.resolve_ids = orig
    assert calls
