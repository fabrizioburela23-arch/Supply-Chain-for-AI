"""Investigación de PRIVADAS (2026-10-22, «HongShan: 0 conclusiones, ¿para qué está la IA?»): los analistas ahora
reciben la FICHA INVESTIGADA de los lotes importados (riesgos, hitos, rondas, estados reportados, posición de mercado,
personas clave — cada bloque con la URL de su fuente) y las inversiones/alianzas (invest/partner, rotuladas como NO
suministro). Antes solo veían role/supplies/moat/growth y devolvían claims=[]."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SECRET_KEY', 'test')

NODE = {
    'id': 'Hithium', 'label': 'Hithium', 'founded': '2019', 'hq_city': 'Xiamen', 'status': 'private',
    'risks': [{'kind': 'financial', 'text_es': 'Primer año rentable recién en 2024.', 'as_of': '2025-03-27',
               'source_url': 'https://www.ess-news.com/2025/03/27/hithium-files/'}],
    'timeline': [{'date': '2023-07-05', 'kind': 'funding', 'text_es': 'Cierra ronda Serie C.',
                  'source_url': 'https://energy-storage.news/hithium-raises/'}],
    'funding': [{'date': '2023-07-05', 'round': 'Serie C', 'amount': 621000000.0, 'currency': 'USD',
                 'lead_investors': [{'name': 'China Life Private Equity'}], 'status': 'closed',
                 'source_url': 'https://energy-storage.news/hithium-raises/'}],
    'financials': {'annual': [{'fiscal_year': 2024, 'revenue': {'value': 12920000000.0, 'currency': 'CNY',
                                                                'source_url': 'https://www.ess-news.com/x/'}}]},
    'market_position': [{'market': 'Baterías de almacenamiento', 'region': 'GLOBAL', 'metric': 'shipments',
                         'rank': 3, 'share_pct': 11.0, 'period': '2024', 'as_of': '2025-03-27',
                         'source_url': 'https://www.ess-news.com/x/'}],
    'key_people': [{'name': 'Wu Zuyu', 'role': 'presidente', 'as_of': '2026-06-25',
                    'source_url': 'https://en.hithium.com/newsroom/'}],
}


def test_ficha_evidence_trae_cada_bloque_con_su_fuente():
    from research.context import ficha_evidence
    ev = {t: (txt, ref, rel) for t, txt, ref, rel in ficha_evidence(NODE)}
    titles = ' | '.join(ev)
    for frag in ('Datos de identidad', 'Riesgos documentados', 'Hitos', 'Rondas de financiación',
                 'Estados financieros reportados', 'Posición de mercado', 'Personas clave'):
        assert frag in titles, frag
    ronda = next(v for k, v in ev.items() if k.startswith('Rondas'))
    assert 'Serie C' in ronda[0] and '621.0M USD' in ronda[0] and 'China Life' in ronda[0]
    assert ronda[1] == 'https://energy-storage.news/hithium-raises/'
    est = next(v for k, v in ev.items() if k.startswith('Estados'))
    assert 'FY2024: ingresos 12.92B CNY' in est[0] and est[1] == 'https://www.ess-news.com/x/'
    pos = next(v for k, v in ev.items() if k.startswith('Posición'))
    assert 'puesto 3' in pos[0] and 'cuota 11.0 %' in pos[0]


def test_ficha_sin_datos_no_inventa_nada():
    from research.context import ficha_evidence
    assert ficha_evidence({'id': 'X', 'label': 'X'}) == []


def test_las_cifras_de_la_ficha_respaldan_lo_que_escriba_el_analista():
    from core.numbers import evidence_numbers, unsupported_figures
    from research.context import ficha_evidence
    vals = evidence_numbers([{'title': t, 'excerpt': x} for t, x, _r, _c in ficha_evidence(NODE)])
    assert unsupported_figures('Cerró una Serie C de 621 millones de dólares', vals) == []
    assert unsupported_figures('Ingresos de 12,9 mil millones de CNY en 2024', vals) == []


def test_inversiones_entran_rotuladas_como_no_suministro():
    from research.context import ContextBuilder, holdings_lines
    lines = holdings_lines('SoftBank')
    assert any(l.startswith('invierte en OpenAI') for l in lines)
    ctx = ContextBuilder(fetchers={'news': lambda *a: [], 'company_news': lambda *a: [], 'profile': lambda *a: {},
                                   'financials': lambda *a: {}, 'candles': lambda *a: [], 'mcap': lambda *a: None,
                                   'sec_filings': lambda *a: [], 'web': lambda *a: []}).build('SoftBank', 'supply_chain')
    hold = [e for e in ctx['evidence'] if 'Inversiones y alianzas' in e['title']]
    assert hold and 'NO son relaciones de suministro' in hold[0]['title'] and 'OpenAI' in hold[0]['excerpt']
