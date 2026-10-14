"""tests/test_instruments.py — empresa ≠ instrumento (BRECHAS_V2 L3-13, decisión #9 sin responder).

  · cada empresa cotizada del catálogo da UN instrumento primario = su `mkt` de hoy (nada se cambia solo);
  · bolsa y moneda salen del sufijo (GBp en Londres, JPY en Tokio…), y los pares FX que hacen falta se siembran;
  · la lista de revisión tiene los 16 casos con varios listados y los 28 con certificado OTC/ADR, con la
    alternativa local deducida del texto, y docs/REVISION_INSTRUMENTOS.md los lista todos con columnas ✔/✘;
  · la siembra en la base es idempotente (solo INSERT … ON CONFLICT DO NOTHING).
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')


@pytest.fixture(scope='module')
def nodes():
    with open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8') as fh:
        return json.load(fh)['nodes']


def test_un_primario_por_empresa_cotizada_igual_al_mkt_de_hoy(nodes):
    from core import instruments as I
    prim = I.from_catalog(nodes)
    listed = {n['id']: n['mkt'].upper() for n in nodes if n.get('mkt')}
    by_company = {}
    for i in prim:
        by_company.setdefault(i['company_id'], []).append(i)
        assert i['is_primary'] and i['id'] == i['ticker']
    # cada símbolo una vez; cada empresa con símbolo único tiene su instrumento, igual a su mkt
    assert len({i['id'] for i in prim}) == len(prim)
    for cid, lst in by_company.items():
        assert len(lst) == 1 and lst[0]['id'] == listed[cid]
    assert len(prim) == len(set(listed.values()))


def test_bolsa_moneda_y_tipo(nodes):
    from core import instruments as I
    assert I.exchange_info('8035.T')[:2] == ('Tokyo (TSE)', 'JPY')
    assert I.exchange_info('OXIG.L')[1] == 'GBp' and I.major_ccy('GBp') == ('GBP', 0.01)
    assert I.exchange_info('NVDA')[1] == 'USD' and I.exchange_info('JPYUSD=X')[1] == 'USD'
    by = {n['id']: n for n in nodes}
    assert I.classify(by['Samsung']) == {'kind': 'otc', 'review': 'otc_adr'}
    assert I.classify(by['TEL'])['kind'] == 'equity'   # lote K: TEL = 8035.T (TOELY pasó a listado secundario)
    assert I.classify(by['Tencent']) == {'kind': 'otc', 'review': 'multi_listed'}
    assert I.classify(by['Nvidia']) == {'kind': 'equity', 'review': None}
    ref = I.reference_instruments(['JPY', 'GBp', 'USD', 'EUR'])
    ids = [r['id'] for r in ref]
    assert ids[:2] == ['SPY', '^IRX'] and {'JPYUSD=X', 'GBPUSD=X', 'EURUSD=X'} <= set(ids) and 'USDUSD=X' not in ids


def test_lista_de_revision_16_mas_28_con_alternativa_local(nodes):
    from core import instruments as I
    rows = I.review_list(nodes)
    multi = [r for r in rows if r['review'] == 'multi_listed']
    otc = [r for r in rows if r['review'] == 'otc_adr']
    assert len(multi) == 21 and len(otc) == 25   # lote K: +5 listados secundarios declarados
    by = {r['id']: r for r in rows}
    assert by['Samsung']['alternative'] == '005930.KS' and by['Samsung']['recommend'] == 'local'
    # lote K: TEL cotiza por 8035.T (principal) y el ADR TOELY es el listado secundario declarado
    assert by['TEL']['current'] == '8035.T' and by['TEL']['alternative'] == 'TOELY'
    assert by['Foxconn']['alternative'] == '2317.TW'
    assert by['Baidu']['alternative'] == '9888.HK' and by['Baidu']['recommend'] == 'keep'
    assert by['Tencent']['alternative'] == '0700.HK' and by['Tencent']['recommend'] == 'local'
    assert by['CNOOC']['alternative'] == '600938.SS'            # el otro listado, nunca el mismo de hoy
    assert all(r['alternative'] != r['current'] for r in rows)


def test_documento_de_revision_lista_todos_los_casos_con_columnas(nodes):
    from core import instruments as I
    doc = open(os.path.join(ROOT, 'docs', 'REVISION_INSTRUMENTOS.md'), encoding='utf-8').read()
    for r in I.review_list(nodes):
        assert f"(`{r['id']}`)" in doc, r['id']
        assert f"`{r['current']}`" in doc
    assert '¿Mantener el de hoy?' in doc and '¿Cambiar a la otra?' in doc and doc.count('✔ / ✘') == 2 * 46
    assert 'nada cambia solo' in doc


@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema
    assert init_schema(retries=1)
    yield _get_engine()


def test_siembra_idempotente(db, nodes):
    from sqlalchemy import text

    from core import instruments as I
    from ontology.db import session_scope
    with session_scope() as s:
        I.seed(s, nodes)
    with session_scope() as s:
        assert I.seed(s, nodes) == 0                    # la segunda vez no inserta ni pisa nada
        n, rev = s.execute(text("SELECT count(*), count(*) FILTER (WHERE review IS NOT NULL) FROM instruments "
                                "WHERE source = 'catalog'")).first()
        sam = s.execute(text("SELECT company_id, kind, review, is_primary FROM instruments WHERE id = 'SSNLF'")).first()
        fx = s.execute(text("SELECT count(*) FROM instruments WHERE kind = 'fx'")).scalar()
    assert n >= len(I.from_catalog(nodes)) and rev >= 44
    assert tuple(sam) == ('Samsung', 'otc', 'otc_adr', True)
    assert fx >= 20
