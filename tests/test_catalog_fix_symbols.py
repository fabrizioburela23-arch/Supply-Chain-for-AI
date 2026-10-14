"""tests/test_catalog_fix_symbols.py — los 19 símbolos del lote 2026-10-14 (existentes_simbolos_revisar.csv).

Regla: la cotización principal es la de la bolsa de origen; los ADR/OTC quedan como listados SECUNDARIOS declarados
en `listings` de la ficha (misma forma que escribe el importador) y sembrados en `instruments` con is_primary False.
  · corregidos en nodes/*.js: SiTime SITM, SK Hynix 000660.KS, QinetiQ QQ.L, TEL 8035.T (+TOELY), Ajinomoto 2802.T
    (+AJINY), Siemens Energy ENR.DE (+SMNEY), Vulcan VUL.AX, TSMC = TSM (sigue siendo el que cotiza la UI) + 2330.TW;
  · confirmados sin cambio: Enflame, Moore Threads, Meeza, Mindspace; los «dado de baja» (Uniper, Northern Data,
    Qorvo, Asetek, ASM) y Astroscale/Kazatomprom quedan para Fabrizio porque contradicen nodes/listing_status.js
    (GENERADO: no se edita a mano) — los 19 están en docs/REVISION_INSTRUMENTOS.md §3;
  · core/instruments: el primario sigue siendo el `mkt` (nada cambia solo), los secundarios se siembran aparte, NRS y
    kernel no dependen de tickers (la auditoría del grafo no empeora y el snapshot sigue con 937/2.510).
"""
import csv
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import instruments as I  # noqa: E402

CSV = os.path.join(ROOT, 'data', 'import', 'lotes', '2026-10-14', 'existentes_simbolos_revisar.csv')
DATABASE_URL = os.getenv('DATABASE_URL', '')

# id → (mkt esperado, símbolos secundarios con símbolo de Yahoo)
APPLIED = {
    'SiTime': ('SITM', []), 'SKHynix': ('000660.KS', []), 'qinetiq': ('QQ.L', []),
    'TEL': ('8035.T', ['TOELY']), 'Ajinomoto': ('2802.T', ['AJINY']), 'SiemensEnergy': ('ENR.DE', ['SMNEY']),
    'VulcanEnergy': ('VUL.AX', []), 'TSMC': ('TSM', ['2330.TW']),
}
UNCHANGED = {'enflame': '688801.SS', 'moorethreads': '688795.SS', 'Meeza': 'MEZA.QA',
             'Mindspace Business Parks REIT': 'MINDSPACE.NS', 'Uniper': 'UN01.DE', 'northern-data': 'NB2.DE',
             'Qorvo': 'QRVO', 'Asetek': 'ASTK.CO', 'AustralianStrategicMaterials': 'ASM.AX',
             'Kazatomprom': 'KAP.L', 'astroscale': '5034.T'}


@pytest.fixture(scope='module')
def snap():
    with open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8') as fh:
        return json.load(fh)


@pytest.fixture(scope='module')
def by(snap):
    return {n['id']: n for n in snap['nodes']}


def test_los_19_del_csv_estan_todos_cubiertos():
    ids = {r['khipus_id'] for r in csv.DictReader(open(CSV, encoding='utf-8'))}
    assert len(ids) == 19
    assert ids == set(APPLIED) | set(UNCHANGED)
    assert ids == {r[0] for r in I.LOT_2026_10_14}


def test_corregidos_en_el_catalogo_con_fuente(by):
    for cid, (mkt, secs) in APPLIED.items():
        n = by[cid]
        assert n['mkt'] == mkt, (cid, n['mkt'])
        ls = I.listings_of(n)
        assert ls, cid
        prim = [l for l in ls if l['is_primary']]
        assert len(prim) == 1 and prim[0]['yahoo_symbol'] == mkt, cid
        assert all(l['source_url'] and l['source_url'].startswith('https://') and l['as_of'] == '2026-10-14' for l in ls)
        assert [l['yahoo_symbol'] for l in I.secondary_listings(n)] == secs, cid
    # SiTime venía duplicada (SITT en nodes_expand2.js y SITS en nodes_spacex.js): el merge ya no ve ninguna de las dos
    assert 'SITT' not in by['SiTime']['ticker'] and 'SITS' not in by['SiTime']['ticker']
    assert by['qinetiq']['ticker'].startswith('QQ · ')
    # TSMC: el ADR sigue siendo lo que cotiza la UI; la bolsa de origen queda declarada como `home`
    tsmc = I.listings_of(by['TSMC'])
    home = next(l for l in tsmc if l['home'])
    assert home['yahoo_symbol'] == '2330.TW' and not home['is_primary'] and home['currency'] == 'TWD'
    adr = next(l for l in tsmc if l['is_primary'])
    assert adr['kind'] == 'adr' and adr['ordinary_per_depositary'] == 5
    # Vulcan: el listado de Fráncfort queda anotado SIN símbolo de Yahoo (no se inventa) y no cuenta como secundario
    vul = I.listings_of(by['VulcanEnergy'])
    assert [l['yahoo_symbol'] for l in vul] == ['VUL.AX', None] and I.secondary_listings(by['VulcanEnergy']) == []


def test_sin_cambio_los_confirmados_y_los_que_decide_fabrizio(by):
    for cid, mkt in UNCHANGED.items():
        assert by[cid]['mkt'] == mkt, (cid, by[cid]['mkt'])
    # Astroscale: la fila cruda ya dice 186A.T, pero listing_status.js (generado) sigue imponiendo 5034.T (unerry)
    assert by['astroscale']['listing']['ticker'] == '5034.T'
    assert [l['yahoo_symbol'] for l in I.listings_of(by['astroscale'])] == ['186A.T']
    assert I.local_alternative(by['astroscale']) == '186A.T'
    # ninguno de los de listing_status.js se tocó a mano: siguen con su nota y fuente generadas
    for cid in ('Uniper', 'northern-data', 'Qorvo', 'Asetek', 'Kazatomprom', 'Meeza', 'enflame', 'moorethreads'):
        assert by[cid]['listing']['source_url'] and by[cid]['listing']['status'] == 'public', cid


def test_instrumentos_primario_sigue_siendo_el_mkt_y_secundarios_aparte(snap, by):
    nodes = snap['nodes']
    prim = I.from_catalog(nodes)
    assert all(i['is_primary'] for i in prim)
    pm = {i['company_id']: i for i in prim}
    for cid, (mkt, secs) in APPLIED.items():
        assert pm[cid]['id'] == mkt
        assert pm[cid]['note'].get('secondaries', []) == secs
    assert pm['TSMC']['kind'] == 'adr' and pm['TEL']['kind'] == 'equity' and pm['SKHynix']['kind'] == 'equity'
    sec = I.secondary_from_catalog(nodes)
    ids = {s['id']: s for s in sec}
    assert set(ids) == {'TOELY', 'AJINY', 'SMNEY', '2330.TW', '186A.T'}
    assert not any(s['is_primary'] for s in sec) and not (set(ids) & {i['id'] for i in prim})
    assert ids['TOELY']['exchange'] == 'OTC (EE.UU.)' and ids['TOELY']['kind'] == 'adr'
    assert ids['TOELY']['note']['primary'] == '8035.T' and 'dado de baja' in ids['TOELY']['note']['note']
    assert ids['2330.TW'] == dict(ids['2330.TW'], exchange='Taiwán (TWSE)', currency='TWD', kind='equity',
                                  company_id='TSMC') and ids['2330.TW']['note']['home'] is True
    allx = I.all_instruments(nodes)
    assert {i['id'] for i in allx} >= set(ids) | {'TWDUSD=X', 'JPYUSD=X', 'KRWUSD=X', 'SPY', '^IRX'}
    assert len({i['id'] for i in allx}) == len(allx)
    assert I.exchange_info('KAP.IL') == ('Londres (LSE IOB, GDR)', 'USD', False)


def test_clasificacion_y_lista_de_revision(by, snap):
    assert I.classify(by['TEL']) == {'kind': 'equity', 'review': 'multi_listed'}
    assert I.classify(by['TSMC']) == {'kind': 'adr', 'review': 'multi_listed'}
    assert I.classify(by['SKHynix']) == {'kind': 'equity', 'review': None}
    assert I.classify(by['SiTime']) == {'kind': 'equity', 'review': None}
    assert I.classify(by['Samsung']) == {'kind': 'otc', 'review': 'otc_adr'}          # sin listings: como siempre
    rows = {r['id']: r for r in I.review_list(snap['nodes'])}
    assert rows['TEL']['alternative'] == 'TOELY' and rows['TEL']['alternative_exchange'] == 'OTC (EE.UU.)'
    assert rows['TEL']['recommend'] == 'keep' and rows['TEL']['declared'] == ['TOELY']
    assert rows['TSMC']['alternative'] == '2330.TW' and rows['TSMC']['recommend'] == 'keep'
    assert 'SiemensEnergy' in rows and rows['SiemensEnergy']['review'] == 'multi_listed'
    for cid in ('SKHynix', 'SiTime', 'qinetiq', 'VulcanEnergy'):
        assert cid not in rows, cid
    assert rows['Samsung']['alternative'] == '005930.KS'            # los casos de antes siguen igual


def test_documento_de_revision_tiene_la_seccion_del_lote(snap):
    doc = open(os.path.join(ROOT, 'docs', 'REVISION_INSTRUMENTOS.md'), encoding='utf-8').read()
    sec = '\n'.join(I.lot_review_markdown())
    assert sec in doc
    assert '## 3. Lote 2026-10-14' in doc and doc.index('## 3. Lote') < doc.index('## Qué pasa después')
    for cid, label, before, after, action, src, note in I.LOT_2026_10_14:
        assert f'(`{cid}`)' in doc and src in doc, cid
    assert sum(1 for r in I.LOT_2026_10_14 if r[4] == 'applied') == 8
    assert sum(1 for r in I.LOT_2026_10_14 if r[4] == 'fabrizio') == 7
    assert '186A' in doc and 'KAP.IL' in doc
    # las filas de la lista de revisión siguen todas en el documento (el generador no se rompió)
    for r in I.review_list(snap['nodes']):
        assert f"(`{r['id']}`)" in doc and f"`{r['current']}`" in doc


def test_snapshot_sigue_con_937_y_2510_y_la_auditoria_no_empeora(snap):
    from scripts.audit_graph import audit_snapshot
    assert snap['counts']['nodes'] == 937 and snap['counts']['links'] == 2510
    base = json.load(open(os.path.join(ROOT, 'data', 'graph_audit_baseline.json'), encoding='utf-8'))['metrics']
    got = audit_snapshot(snap)['metrics']
    for k, v in base.items():
        assert got[k] <= v, (k, got[k], v)
    assert got['duplicate_entities'] == 0      # SITM una sola vez; ningún mkt repetido


@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema
    assert init_schema(retries=1)
    yield _get_engine()


def test_siembra_secundarios_y_detecta_primarios_en_conflicto(db, snap):
    from sqlalchemy import text

    from ontology.db import session_scope
    nodes = snap['nodes']
    with session_scope() as s:
        I.seed(s, nodes)
        rows = {r[0]: r for r in s.execute(text("SELECT id, company_id, is_primary, kind, exchange, note FROM "
                                                 "instruments WHERE id IN ('TOELY','8035.T','2330.TW','TSM')")).all()}
        assert rows['TOELY'][1:4] == ('TEL', False, 'adr') and rows['TOELY'][4] == 'OTC (EE.UU.)'
        assert rows['8035.T'][1:3] == ('TEL', True) and rows['TSM'][1:4] == ('TSMC', True, 'adr')
        assert rows['2330.TW'][1:3] == ('TSMC', False) and rows['2330.TW'][5]['home'] is True
        assert I.seed(s, nodes) == 0
        assert I.primary_conflicts(s) == []
        # un primario viejo que quedó en la base (la siembra nunca pisa) aparece como conflicto
        s.execute(text("INSERT INTO instruments (id, company_id, ticker, exchange, currency, kind, is_primary, source) "
                       "VALUES ('HXSCL', 'SKHynix', 'HXSCL', 'OTC', 'USD', 'otc', true, 'catalog') "
                       "ON CONFLICT DO NOTHING"))
        assert I.primary_conflicts(s) == [{'company_id': 'SKHynix', 'primaries': ['000660.KS', 'HXSCL']}]
        s.execute(text("DELETE FROM instruments WHERE id = 'HXSCL'"))
