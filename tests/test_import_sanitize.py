"""tests/test_import_sanitize.py — lote L (2026-10-15): el saneador de FORMATO de las fichas khipus.company/1
(core/import_normalize.sanitize_record). Regla por regla; PURO (no toca la entrada), DETERMINISTA e IDEMPOTENTE
(sanear dos veces = sanear una; registro vacío la segunda vez); NO INVENTA (todo valor de la salida está en la ficha
original o en un cambio registrado); NINGÚN número cambia (los que sobreviven son idénticos); lo irreparable se quita
—solo ese campo— y queda en el registro con su valor; una ficha se rechaza solo si su identidad queda inservible.
Las mismas propiedades se comprueban sobre las 386 fichas REALES del lote (data/import/lotes/2026-10-15)."""
import copy
import gzip
import json
import os
import re
import sys
from collections import Counter

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('KHIPU_SCHEDULER', 'off')

from core import import_normalize as N  # noqa: E402
from ontology import company_schema as CS  # noqa: E402

LOTE = os.path.join(ROOT, 'data', 'import', 'lotes', '2026-10-15')
F = {'source_url': 'https://www.sec.gov/x', 'source_kind': 'primary', 'as_of': '2025-06', 'confidence': 0.9}
BASE = {
    'schema': 'khipus.company/1', 'record_id': 't-001',
    'research_meta': {'researcher': 'x', 'researched_at': '2026-10-14T10:00:00Z', 'method': 'manual', 'tier': 'A'},
    'identity': {'legal_name': {'value': 'Test Co', **F}, 'short_name': 'Test', 'status': {'value': 'public', **F},
                 'hq_country': {'value': 'SE', **F}},
    'classification': {'cat': 'foundry'},
    'profile': {'summary': {'value': 'Empresa de prueba larga', 'value_en': 'Test company long enough', **F}},
}
EVID = [{'source_url': 'https://www.sec.gov/y', 'as_of': '2025', 'source_kind': 'press', 'quote': 'q'}]
REL = {'relation_id': 'rel-001', 'counterparty': {'name': 'Apple', 'khipus_id': 'Apple'}, 'rel_type': 'supply',
       'this_role': 'supplier', 'label_es': 'provee chips', 'label_en': 'supplies chips', 'status': 'active',
       'dependency': {'criticality': 3}, 'confidence': 0.7, 'evidence': EVID}
LST = {'is_primary': True, 'source_url': 'https://ex.com/l', 'as_of': '2026'}


def _rec(**kw):
    d = copy.deepcopy(BASE)
    for k, v in kw.items():
        d[k] = v
    return d


def _san(d):
    out, log = N.sanitize_record(d)
    return out, log, CS.validate_record(out)[0] is not None


def _rules(log):
    return [e['rule'] for e in log]


# ── reglas una por una ──────────────────────────────────────────────────────────────────────────────────────────
def test_url_con_espacios_y_corchetes_se_codifica_sin_tocar_el_servidor():
    u = 'https://api.gleif.org/api/v1/lei-records?filter[fulltext]=Doosan Enerbility&page[size]=20'
    assert N.encode_url(u) == ('https://api.gleif.org/api/v1/lei-records?filter%5Bfulltext%5D=Doosan%20Enerbility'
                               '&page%5Bsize%5D=20')
    assert N.encode_url(N.encode_url(u)) == N.encode_url(u)                 # idempotente: '%' no se recodifica
    assert N.encode_url('  https://ex.com/a%20b.pdf ') == 'https://ex.com/a%20b.pdf'
    assert N.encode_url('https://ex.com/x　y') == 'https://ex.com/x%E3%80%80y'   # espacio Unicode → UTF-8
    d = _rec()
    d['profile']['summary']['source_url'] = 'https://www.riber.com/findocs/4159-RIBER-RAPPORT ANNUEL 2025.pdf'
    d['research_meta']['sources_consulted'] = ['https://ex.com/[a] b', 'https://ex.com/ok']
    out, log, ok = _san(d)
    assert ok and out['profile']['summary']['source_url'].endswith('RAPPORT%20ANNUEL%202025.pdf')
    assert out['research_meta']['sources_consulted'] == ['https://ex.com/%5Ba%5D%20b', 'https://ex.com/ok']
    assert Counter(_rules(log)) == {'url_percent_encode': 2}
    assert {e['path'] for e in log} == {'profile.summary.source_url', 'research_meta.sources_consulted[0]'}


def test_anio_fiscal_como_texto_y_partido():
    fin = {'annual': [{'fiscal_year': '2025'}, {'fiscal_year': 'FY2024'}, {'fiscal_year': '2025/26', 'revenue': {
        'value': 446.6, 'currency': 'CHF', 'period': 'FY2025/26', **F}}]}
    out, log, ok = _san(_rec(financials=fin))
    assert ok
    assert [a['fiscal_year'] for a in out['financials']['annual']] == [2025, 2024, 2026]
    assert out['financials']['annual'][2]['revenue']['period'] == 'FY2026'
    assert out['financials']['annual'][2]['revenue']['value'] == 446.6          # el número no se toca
    assert Counter(_rules(log)) == {'fiscal_year_text_to_int': 2, 'fiscal_year_split_end': 1, 'period_fy_split_end': 1}
    # un "partido" que no es de 12 meses no se adivina: el año queda inválido y se quita SOLO ese ejercicio
    out2, log2, ok2 = _san(_rec(financials={'annual': [{'fiscal_year': '2025/27'}, {'fiscal_year': 2024}]}))
    assert ok2 and out2['financials']['annual'] == [{'fiscal_year': 2024}]
    assert [e['rule'] for e in log2] == ['drop_invalid'] and log2[0]['path'] == 'financials.annual[0]'


def test_ticker_con_espacio_lleva_guion_en_ids_cotizaciones_y_contrapartes():
    d = _rec(listings=[dict(LST, ticker='ERIC B', exchange_mic='XSTO', yahoo_symbol='ERIC-B.ST', currency='SEK', kind='equity')],
             relations=[dict(REL, counterparty={'name': 'Maersk', 'ids': {'ticker': 'MAERSK B', 'exchange_mic': 'XCSE'}})])
    d['identity']['ids'] = {'ticker': 'ERIC B', 'yahoo_symbol': 'ERIC-B.ST'}
    out, log, ok = _san(d)
    assert ok and out['identity']['ids']['ticker'] == 'ERIC-B' and out['listings'][0]['ticker'] == 'ERIC-B'
    assert out['relations'][0]['counterparty']['ids']['ticker'] == 'MAERSK-B'
    assert Counter(_rules(log)) == {'ticker_space_to_dash': 3}


def test_khipus_id_viejo_de_la_contraparte_pasa_a_id_hint_y_nunca_se_pierde():
    d = _rec(relations=[dict(REL, counterparty={'name': 'Lockheed Martin', 'khipus_id': 'lockheed-martin'}),
                        dict(REL, relation_id='rel-002', counterparty={'name': '50Hertz Transmission GmbH', 'khipus_id': '50Hertz'}),
                        dict(REL, relation_id='rel-003', counterparty={'name': 'Raro', 'khipus_id': 'a/b'})],
             corporate={'subsidiaries': [{'entity': {'name': 'CBRE', 'khipus_id': 'CBRE Group'}}]})
    out, log, ok = _san(d)
    assert ok
    cps = [r['counterparty'] for r in out['relations']]
    assert cps[0] == {'name': 'Lockheed Martin', 'id_hint': 'lockheed-martin'}
    assert cps[1] == {'name': '50Hertz Transmission GmbH', 'id_hint': '50Hertz'}
    assert cps[2] == {'name': 'Raro'}                                          # ni id nuevo ni id del grafo
    assert out['corporate']['subsidiaries'][0]['entity'] == {'name': 'CBRE', 'id_hint': 'CBRE Group'}
    moved = [e for e in log if e['rule'] == 'counterparty_id_to_hint']
    assert [e['action'] for e in moved] == ['move', 'move', 'drop', 'move']
    assert moved[2]['before'] == 'a/b'                                          # el valor quitado queda en el registro


def test_cotizacion_deriva_lo_que_sale_de_si_misma():
    lst = [
        dict(LST, ticker='CYPC', exchange_mic='XLON', currency='USD', kind='gdr', is_primary=False),        # → CYPC.IL
        dict(LST, ticker='TEEG', exchange_mic='XLON', kind='gdr', is_primary=False),                       # → .IL + USD
        dict(LST, ticker='VOLV-B', exchange_mic='XSTO', currency='SEK', kind='equity'),                    # → VOLV-B.ST
        dict(LST, yahoo_symbol='MAERSK-A.CO', ticker='MAERSK-A', currency='DKK', kind='dual_class', is_primary=False),  # → XCSE
        dict(LST, exchange_mic='XBUE', yahoo_symbol='BAC.BA', currency='ARS', kind='equity', is_primary=False),  # → BAC
        dict(LST, ticker='600900', exchange_mic='XSHG', yahoo_symbol='600900.SS', currency='CNY', is_primary=False),  # → a_share
    ]
    d = _rec(listings=lst)
    d['identity']['hq_country']['value'] = 'CN'
    out, log, ok = _san(d)
    assert ok, CS.validate_record(out)[1][:3]
    o = out['listings']
    assert (o[0]['yahoo_symbol'], o[1]['yahoo_symbol'], o[1]['currency']) == ('CYPC.IL', 'TEEG.IL', 'USD')
    assert o[2]['yahoo_symbol'] == 'VOLV-B.ST' and o[3]['exchange_mic'] == 'XCSE' and o[4]['ticker'] == 'BAC'
    assert o[5]['kind'] == 'a_share'
    assert Counter(_rules(log)) == {'listing_yahoo_from_ticker_mic': 3, 'listing_currency_from_yahoo': 1,
                                    'listing_mic_from_yahoo': 1, 'listing_ticker_from_yahoo': 1,
                                    'listing_kind_home_exchange': 1}


def test_certificado_cuyo_simbolo_no_es_de_la_empresa_se_quita():
    """Revisión del lote L: Boeing traía un CEDEAR «BAC.BA» (el de Bank of America) sin ticker; derivar BAC lo hacía
    pasar por bueno. Un certificado sin ticker cuyo símbolo de Yahoo no es ningún ticker de la ficha se quita entero
    (con registro); si coincide con un ticker declarado, se deriva como siempre."""
    lst = [dict(LST, ticker='BA', exchange_mic='XNYS', yahoo_symbol='BA', currency='USD', kind='equity'),
           dict(LST, exchange_mic='XBUE', yahoo_symbol='BAC.BA', currency='ARS', kind='gdr', is_primary=False),
           dict(LST, exchange_mic='XBUE', yahoo_symbol='BA.BA', currency='ARS', kind='gdr', is_primary=False)]
    out, log, ok = _san(_rec(listings=lst))
    assert ok, CS.validate_record(out)[1][:3]
    assert [l.get('yahoo_symbol') for l in out['listings']] == ['BA', 'BA.BA'] and out['listings'][1]['ticker'] == 'BA'
    conf = [e for e in log if e['rule'] == 'listing_ticker_conflict']
    assert len(conf) == 1 and conf[0]['action'] == 'drop' and conf[0]['path'] == 'listings[1]'
    assert conf[0]['before']['yahoo_symbol'] == 'BAC.BA'                       # el valor quitado queda en el registro
    out2, log2, _ok = _san(out)
    assert log2 == [] and out2 == out                                          # idempotente


def test_cotizacion_que_no_se_puede_completar_se_quita_entera_con_registro():
    lst = [dict(LST, ticker='KAP', exchange_mic='AIXK', kind='equity'),                                       # bolsa sin sufijo
           dict(LST, ticker='DNNGY', yahoo_symbol='DNNGY', currency='USD', kind='adr', is_primary=False),     # '' = varias bolsas
           dict(LST, ticker='A1ON34', exchange_mic='BVMF', yahoo_symbol='A1ON34.SA', currency='BRL', is_primary=False),  # tipo?
           dict(LST, ticker='SAND', exchange_mic='XSTO', yahoo_symbol='SAND.ST', currency='SEK', kind='equity')]
    d = _rec(listings=lst)
    d['identity']['hq_country']['value'] = 'IE'
    out, log, ok = _san(d)
    assert ok and [l['ticker'] for l in out['listings']] == ['SAND']
    drops = [e for e in log if e['action'] == 'drop']
    assert [e['path'] for e in drops] == ['listings[0]', 'listings[1]', 'listings[2]']
    assert drops[0]['before']['ticker'] == 'KAP' and all(e['rule'] == 'drop_invalid' for e in drops)


def test_campo_en_vivo_y_desconocido_se_quitan_y_lo_largo_solo_ese_campo():
    d = _rec(price=123.4, listings=[dict(LST, ticker='TRTN', exchange_mic='XNYS', yahoo_symbol='TRTN', currency='USD',
                                         kind='preferred', share_class='x' * 120)])
    d['identity']['foo'] = 1
    out, log, ok = _san(d)
    assert ok and 'price' not in out and 'foo' not in out['identity']
    assert out['listings'][0]['ticker'] == 'TRTN' and 'share_class' not in out['listings'][0]
    by = {e['path']: e for e in log}
    assert by['price']['rule'] == 'drop_forbidden_live_field' and by['price']['before'] == 123.4
    assert by['identity.foo']['rule'] == 'drop_unknown_field'
    assert by['listings[0].share_class']['rule'] == 'drop_invalid'


def test_flujo_sin_criticidad_se_quita_y_owns_sin_dependency_se_queda():
    rels = [{k: v for k, v in REL.items() if k != 'dependency'},
            dict({k: v for k, v in REL.items() if k != 'dependency'}, relation_id='rel-002', rel_type='owns', this_role='owned'),
            dict(REL, relation_id='rel-003', rel_type='invest', this_role='investor',
                 dependency={'contract_value': {'value': 2.15e10, 'currency': 'CNY', **F}})]
    out, log, ok = _san(_rec(relations=rels))
    assert ok and [r['relation_id'] for r in out['relations']] == ['rel-002', 'rel-003']
    assert out['relations'][1]['dependency']['contract_value']['value'] == 2.15e10
    assert [(e['path'], e['rule']) for e in log] == [('relations[0]', 'drop_invalid')]


def test_identidad_inservible_se_rechaza():
    d = _rec()
    d['identity'].pop('hq_country')
    out, log, ok = _san(d)
    assert not ok and log[-1]['rule'] == 'reject' and log[-1]['action'] == 'reject'
    out2, log2 = N.sanitize_record('no soy una ficha')
    assert log2[0]['rule'] == 'reject'


def test_reglas_conocidas_y_registro_bien_formado():
    d = _rec(financials={'annual': [{'fiscal_year': '2025'}]}, price=1)
    _out, log = N.sanitize_record(d)
    for e in log:
        assert e['rule'] in N.SANITIZE_RULES and e['action'] in ('repair', 'derive', 'move', 'drop', 'reject')
        assert isinstance(e['path'], str) and 'before' in e
        assert ('after' in e) == (e['action'] in ('repair', 'derive', 'move'))


# ── propiedades sobre las 386 fichas REALES ──────────────────────────────────────────────────────────────────────
@pytest.fixture(scope='module')
def reales():
    with gzip.open(os.path.join(LOTE, 'fichas_completas.jsonl.gz'), 'rt', encoding='utf-8') as fh:
        recs = [json.loads(ln) for ln in fh.read().splitlines() if ln.strip()]
    assert len(recs) == 386
    return recs


@pytest.fixture(scope='module')
def saneadas(reales):
    snap = copy.deepcopy(reales)
    out = [N.sanitize_record(r) for r in reales]
    assert reales == snap                                                       # PURO: la entrada no cambia
    return out


def test_las_386_validan_despues_de_sanear(saneadas):
    bad = [r['record_id'] for r, _log in saneadas if CS.validate_record(r)[0] is None]
    assert bad == []
    assert not any(e['rule'] == 'reject' for _r, log in saneadas for e in log)


def test_idempotente_sobre_las_386(saneadas):
    for r, _log in saneadas:
        r2, log2 = N.sanitize_record(r)
        assert log2 == [] and r2 == r, r['record_id']


def test_determinista(reales, saneadas):
    for raw, (r, log) in zip(reales[:60], saneadas[:60]):
        assert N.sanitize_record(raw) == (r, log)


def _leaves(x, key=None):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _leaves(v, k)
    elif isinstance(x, list):
        for v in x:
            yield from _leaves(v, key)
    else:
        yield key, x


def _last_key(path):
    return re.sub(r'\[\d+\]$', '', str(path)).rsplit('.', 1)[-1]


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def test_no_inventa_nada(reales, saneadas):
    """Todo (clave, valor) de la salida está en la ficha original o es el `after` de un cambio registrado."""
    for raw, (out, log) in zip(reales, saneadas):
        allowed = set((k, json.dumps(v)) for k, v in _leaves(raw))
        for e in log:
            if 'after' in e:
                allowed.add((_last_key(e.get('to') or e['path']), json.dumps(e['after'])))
        extra = [(k, v) for k, v in _leaves(out) if (k, json.dumps(v)) not in allowed]
        assert extra == [], (raw['record_id'], extra[:5])


def test_ningun_numero_cambia(reales, saneadas):
    """Números de la salida = números de la original − los de lo quitado + los de las reparaciones de tipo (texto→año)."""
    for raw, (out, log) in zip(reales, saneadas):
        want = Counter((k, v) for k, v in _leaves(raw) if _is_num(v))
        for e in log:
            if e['action'] == 'drop':
                b = e.get('before')
                if _is_num(b):
                    want[(_last_key(e['path']), b)] -= 1
                elif isinstance(b, (dict, list)):
                    for k, v in _leaves(b, _last_key(e['path'])):
                        if _is_num(v):
                            want[(k, v)] -= 1
            elif 'after' in e and _is_num(e['after']):
                assert not _is_num(e['before']), e                              # nunca número → otro número
                want[(_last_key(e['path']), e['after'])] += 1
        got = Counter((k, v) for k, v in _leaves(out) if _is_num(v))
        assert +want == got, raw['record_id']


def test_resumen_de_las_386(saneadas):
    s = N.sanitize_summary([log for _r, log in saneadas])
    assert s['url_percent_encode'] >= 1300 and s['fiscal_year_text_to_int'] == 231 and s['fiscal_year_split_end'] == 1
    assert s['counterparty_id_to_hint'] == 23 and s['ticker_space_to_dash'] == 6 and s['period_fy_split_end'] == 6
    assert s.get('drop_invalid', 0) == 5 and 'reject' not in s and s.get('listing_ticker_conflict') == 1   # Boeing BAC.BA
    drops = sorted(e['path'] for _r, log in saneadas for e in log if e['action'] == 'drop')
    assert drops == ['listings[0]', 'listings[1]', 'listings[1]', 'listings[1]', 'listings[1]', 'listings[2]']   # 6 cotizaciones
