"""Comité y empresas que aún no cotizan (2026-11-10, Fabrizio sobre Anthropic): se evalúan como su SALIDA A BOLSA —
nada de AVOID por no cotizar — y el paquete del presidente trae lo que REPORTAN las noticias del IPO (D2)."""
from types import SimpleNamespace as NS

from research import committee as cm


def test_privada_no_es_avoid_por_no_cotizar():
    assert cm.decide(40, investable=False)[0] == 'HOLD'
    assert cm.decide(0, investable=False)[0] == 'HOLD'
    assert cm.decide(-40, investable=False)[0] == 'AVOID'
    assert 'salida a bolsa' in cm.decide(40, investable=False)[1]


def test_paquete_trae_las_noticias_del_ipo_y_la_nota():
    claims = [{'id': 'a', 'agent_type': 'fundamental', 'stance': 'positive', 'horizon': 'LONG_TERM', 'confidence': 0.7}]
    conv, overall = cm.conviction_by_horizon(claims)
    cb = {'a': NS(agent_type='fundamental', horizon='LONG_TERM', stance='positive', statement_es='Crece fuerte.',
                  statement_en='', reasoning_summary='', falsifiers=[])}
    live = {'ok': True, 'line': '- Anthropic (privada): última valuación VERIFICADA $965B',
            'ipo': {'ok': True, 'source': 'web', 'text': 'Reported IPO target valuation of $2 trillion (Reuters, 2026-11-09).',
                    'citations': [{'url': 'https://example.com/ipo', 'title': 't'}]}}
    sizing = cm.compute_sizing('HOLD', None, cm.mandate_from({}))
    text, items, refs, _c = cm.build_package('Anthropic', None, cb, conv, overall, [], live, {'ok': False}, sizing,
                                             'HOLD', 'x', None)
    assert 'D2' in refs and '2 trillion' in text and 'https://example.com/ipo' in text
    assert 'NO cuentes «no cotiza»' in text


def test_ipo_cae_a_gdelt_sin_claude(monkeypatch):
    from core import ai, company_data
    cm._IPO_CACHE.clear()
    monkeypatch.setattr(ai, 'claude_web_available', lambda: False)
    monkeypatch.setattr(company_data, 'get_valuation_news', lambda name: {
        'latest_talks': {'kind': 'talks', 'headline': 'X in talks to IPO at $2T', 'source': 'reuters.com',
                         'datetime': '20261109', 'url': 'https://r.com/x'}})
    out = cm._default_ipo('x', 'ZZ Test Co')
    assert out['ok'] and '$2T' in out['text'] and out['citations'][0]['url'] == 'https://r.com/x'
    cm._IPO_CACHE.clear()
