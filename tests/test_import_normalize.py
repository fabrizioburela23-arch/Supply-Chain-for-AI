"""tests/test_import_normalize.py — EXPANSION_5K E2.2: las 136 grafías de país del catálogo mapean a ISO-2 (o a una
región), MIC → sufijo de Yahoo, fechas parciales sin inventar el día (GENESIS sin start, nunca "ahora"), dinero en
unidades + ISO 4217, ids de Khipus con el patrón del esquema."""
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import import_normalize as N  # noqa: E402


def _catalog_countries():
    with open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8') as fh:
        g = json.load(fh)
    return Counter(n.get('country') for n in g['nodes'] if n.get('country'))


def test_las_136_grafias_del_catalogo_mapean_a_iso_o_region():
    c = _catalog_countries()
    assert len(c) >= 130
    sin = [k for k in c if N.iso2_of(k) is None and N.region_of(k) is None]
    assert not sin, sin
    assert N.iso2_of('EEUU') == 'US' and N.iso2_of('Estados Unidos (Dallas, TX)') == 'US'
    assert N.iso2_of('Japón') == 'JP' and N.iso2_of('Japon') == 'JP' and N.iso2_of('Corea') == 'KR'
    assert N.iso2_of('Países Bajos (sede en La Haya)') == 'NL' and N.iso2_of('Hong Kong (China)') == 'HK'
    assert N.iso2_of('US') == 'US' and N.iso2_of('KY') == 'KY'


def test_regiones_no_son_paises():
    for r in ('Europa', 'RestoEuropa', 'RestoMundo'):
        assert N.iso2_of(r) is None and N.region_of(r) == r
    assert N.region_of('EEUU') is None


def test_clave_del_catalogo_y_etiquetas():
    assert N.catalog_key_of('US') == 'EEUU' and N.catalog_key_of('JP') == 'Japon' and N.catalog_key_of('GB') == 'ReinoUnido'
    assert N.catalog_key_of('NL') == 'PaisesBajos' and N.catalog_key_of('AE') == 'EAU' and N.catalog_key_of('KR') == 'Corea'
    assert N.country_label('US', 'es') == 'Estados Unidos' and N.country_label('US', 'en') == 'United States'


def test_mic_a_sufijo_yahoo_y_moneda():
    assert N.suffix_of_mic('XNAS') == '' and N.suffix_of_mic('XSHE') == 'SZ' and N.suffix_of_mic('XHKG') == 'HK'
    assert N.suffix_of_mic('XJPX') == 'T' and N.suffix_of_mic('ROCO') == 'TWO' and N.suffix_of_mic('XKOS') == 'KQ'
    assert N.suffix_of_mic('ZZZZ') is None
    assert N.yahoo_symbol_for('2330', 'XTAI') == '2330.TW' and N.yahoo_symbol_for('BRK.B', 'XNYS') == 'BRK-B'
    assert N.yahoo_symbol_for('300750', 'XSHE') == '300750.SZ' and N.yahoo_symbol_for('X', 'ZZZZ') is None
    assert N.yahoo_matches_mic('300750.SZ', 'XSHE') is True and N.yahoo_matches_mic('300750.SS', 'XSHE') is False
    assert N.currency_of_mic('XSHE') == 'CNY' and N.currency_of_mic('XLON') == 'GBP' and N.currency_of_mic('XKLS') == 'MYR'
    assert N.currency_of_mic('OTCM') == 'USD' and N.currency_of_mic('ZZZZ') is None
    # el lote 1 trae estas bolsas: todas con sufijo y moneda
    for mic in ('XSHG', 'XJPX', 'XSHE', 'XNYS', 'XNAS', 'XTAI', 'XNSE', 'XHKG', 'XKOS', 'XKRX', 'ROCO', 'XTSE', 'XETR',
                'XASX', 'XLON', 'XPAR', 'BVMF', 'XKLS', 'XSTO', 'XSES', 'XIDX', 'OTCM', 'XSWX', 'XMIL', 'XOSL', 'XMAD',
                'XTSX', 'MISX', 'XBKK', 'XMEX', 'XBRU', 'XSTU', 'XJSE', 'XTAE', 'XAMS', 'XSAU', 'XIST', 'XBER', 'XSGO'):
        assert N.suffix_of_mic(mic) is not None and N.currency_of_mic(mic), mic


def test_fechas_parciales_no_inventan_el_dia():
    s, e, p = N.partial_date('2021')
    assert (s.isoformat(), e.isoformat(), p) == ('2021-01-01T00:00:00+00:00', '2022-01-01T00:00:00+00:00', 'year')
    s, e, p = N.partial_date('2021-07')
    assert (s.isoformat(), e.isoformat(), p) == ('2021-07-01T00:00:00+00:00', '2021-08-01T00:00:00+00:00', 'month')
    s, e, p = N.partial_date('2021-12-31')
    assert (s.isoformat(), e.isoformat(), p) == ('2021-12-31T00:00:00+00:00', '2022-01-01T00:00:00+00:00', 'day')
    assert N.partial_date('2021-02-30') is None and N.partial_date('ayer') is None and N.partial_date('1899') is None


def test_valid_from_sin_start_es_genesis_y_nunca_ahora():
    from ontology.service import GENESIS_SENTINEL
    assert N.valid_from_of(None) == (GENESIS_SENTINEL, False)
    assert N.valid_from_of('') == (GENESIS_SENTINEL, False)
    assert N.valid_from_of('2021-07') == ('2021-07-01T00:00:00+00:00', True)
    assert N.valid_to_of('2021-07') == '2021-08-01T00:00:00+00:00' and N.valid_to_of(None) is None


def test_dinero_en_unidades_con_moneda():
    m = N.money({'value': 1500000000, 'currency': 'CNY', 'period': 'FY2025', 'as_of': '2026-03', 'source_url': 'https://x.com/a',
                 'confidence': 0.8})
    assert m['value'] == 1500000000.0 and m['currency'] == 'CNY' and m['period'] == 'FY2025'
    assert N.money({'value': 1, 'currency': 'yuan'}) is None and N.money({'value': 'x', 'currency': 'USD'}) is None
    assert N.pct(20.25) == 0.2025 and N.pct('x') is None


def test_ids_de_khipus():
    assert N.khipus_id_from('LG Energy Solution') == 'LGEnergySolution'
    assert N.khipus_id_from('3M') == 'Co3M' and N.is_khipus_id(N.khipus_id_from('3M'))
    assert N.is_khipus_id(N.khipus_id_from('宁德时代')) and N.khipus_id_from('Mahindra & Mahindra') == 'MahindraMahindra'
    assert N.is_khipus_id('TSMC') and not N.is_khipus_id('1abc') and not N.is_khipus_id('a-b')
