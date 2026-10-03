"""core/portfolio_report.py · core/news_feed.py · core/portfolio_reports_api.py (sin red)."""
import os
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

needs_db = pytest.mark.skipif(not os.getenv('DATABASE_URL'), reason='requiere DATABASE_URL')


def _days(n=60):
    d0 = date.today() - timedelta(days=n)
    return [(d0 + timedelta(days=i)).isoformat() for i in range(n + 1)]


def fake_fetch(sym, rng='1y'):
    ds = _days()
    growth = {'AAA': 0.004, 'BBB': -0.002, 'SPY': 0.001}[sym]
    return {d: 100 * (1 + growth) ** i for i, d in enumerate(ds)}, 'USD'


def fake_news(holdings, days=7, limit=12, lang='es'):
    return {'items': [{'title': 'AAA sube', 'published_at': datetime.now(timezone.utc).isoformat(),
                       'holdings': ['Alfa'], 'url': 'https://x/1'}]}


POS = [{'symbol': 'AAA', 'label': 'Alfa', 'shares': 10, 'cost_usd': 900.0},
       {'symbol': 'BBB', 'label': 'Beta', 'shares': 10, 'cost_usd': 1100.0}]


def test_reporte_rendimiento_vs_inicio_y_spy():
    from core import portfolio_report as pr
    rep = pr.build(POS, start_value=2000.0, period='month', fetch=fake_fetch, fx_fn=lambda c: 1.0,
                   advisor=lambda *a, **k: {'ok': False}, news=fake_news)
    assert rep['ok'] and rep['curve'][0]['idx'] == 100.0
    p = rep['performance']
    assert p['initial_usd'] == 2000.0 and p['since_start_usd'] == round(p['value_now_usd'] - 2000.0, 2)
    assert p['spy_period_pct'] is not None and 'vs_spy_pts' in p
    assert rep['contributions'][0]['symbol'] == 'AAA' and rep['contributions'][-1]['contrib_usd'] < 0
    assert rep['news'][0]['title'] == 'AAA sube'
    s = rep['summary']
    assert s['text'] and 'no asesoría' in s['text']
    assert pr.build([], fetch=fake_fetch)['error_code'] == 'no_positions'


def test_noticias_con_fecha_sin_repetir_y_sin_viejas():
    from core import news_feed
    now = datetime.now(timezone.utc)

    def fetch(nid, label, symbol, days):
        return [{'title': f'{label} firma contrato', 'url': f'https://n/{label}', 'outlet': 'x', 'summary': 'ok',
                 'published_at': now - timedelta(hours=3), 'source': 'finnhub'},
                {'title': 'Crisis de gobernanza en Samsung', 'url': 'https://old', 'outlet': 'y', 'summary': '',
                 'published_at': now - timedelta(days=120), 'source': 'gdelt'},                 # vieja: fuera
                {'title': 'Sin fecha', 'url': 'https://nodate', 'published_at': None},          # sin fecha: fuera
                {'title': 'El sector de chips sube', 'url': 'https://shared', 'summary': '',
                 'published_at': now - timedelta(days=4), 'source': 'gdelt'}]                    # compartida
    out = news_feed.portfolio_news([{'label': 'Alfa', 'symbol': 'AAA', 'weight_pct': 70},
                                    {'label': 'Beta', 'symbol': 'BBB', 'weight_pct': 30}], days=7, fetch=fetch)
    titles = [x['title'] for x in out['items']]
    assert 'Crisis de gobernanza en Samsung' not in titles and 'Sin fecha' not in titles
    shared = next(x for x in out['items'] if x['url'] == 'https://shared')
    assert set(shared['holdings']) == {'Alfa', 'Beta'} and shared['freshness'] == 'older'
    assert out['items'][0]['title'] == 'Alfa firma contrato' and out['items'][0]['label'].startswith('🆕')


def test_programacion_due():
    from types import SimpleNamespace as NS

    from core.portfolio_reports_api import due
    fri = datetime(2026, 10, 2, 22, tzinfo=timezone.utc)     # viernes 22:00 UTC
    assert due(NS(schedule='daily', last_report_at=None), fri)
    assert not due(NS(schedule='daily', last_report_at=fri - timedelta(hours=3)), fri)
    assert due(NS(schedule='weekly', last_report_at=fri - timedelta(days=7)), fri)
    assert not due(NS(schedule='weekly', last_report_at=None), fri - timedelta(days=1))
    first = datetime(2026, 11, 1, 7, tzinfo=timezone.utc)
    assert due(NS(schedule='monthly', last_report_at=datetime(2026, 10, 1, 7, tzinfo=timezone.utc)), first)
    assert not due(NS(schedule='off', last_report_at=None), fri)


@needs_db
def test_api_reportes_dueno_y_programados(monkeypatch):
    from ontology.db import init_schema
    init_schema(retries=1)
    import server
    from core import portfolio_report, portfolio_reports_api as api
    monkeypatch.setattr(portfolio_report, 'build', lambda pos, **k: portfolio_report.build.__wrapped__(pos, **k)
                        if hasattr(portfolio_report.build, '__wrapped__') else _fake_build(pos, **k))
    server.app.config['TESTING'] = True
    c = server.app.test_client()
    H = {'X-Khipu-Owner': 'k' * 24}
    r = c.post('/api/portfolio-report/generate', json={'positions': POS, 'period': 'week'}, headers=H)
    assert r.status_code == 200, r.get_json()
    rid = r.get_json()['id']
    lst = c.get('/api/portfolio-report/list', headers=H).get_json()
    assert lst['unread'] >= 1 and lst['reports'][0]['id'] == rid
    assert c.get('/api/portfolio-report/list').status_code == 401                         # sin llave
    assert c.get(f'/api/portfolio-report/{rid}', headers={'X-Khipu-Owner': 'z' * 24}).status_code == 404   # otra llave
    assert c.get(f'/api/portfolio-report/{rid}', headers=H).get_json()['performance']['value_now_usd'] == 123.0
    w = c.post('/api/portfolio-report/watch', json={'source_key': 'pf:1', 'name': 'Mía', 'positions': POS,
                                                    'schedule': 'daily'}, headers=H).get_json()
    assert w['ok'] and w['schedule'] == 'daily'
    n = api.run_due(now=datetime(2026, 10, 2, 22, tzinfo=timezone.utc), build=_fake_build)
    assert n >= 1
    kinds = [x['kind'] for x in c.get('/api/portfolio-report/list', headers=H).get_json()['reports']]
    assert 'daily' in kinds
    assert c.delete(f'/api/portfolio-report/{rid}', headers=H).get_json()['ok']


def _fake_build(pos, **k):
    return {'ok': True, 'lang': 'es', 'performance': {'period_from': '2026-09-01', 'period_to': '2026-10-01',
                                                      'value_now_usd': 123.0, 'period_change_pct': 1.0},
            'summary': {'text': 'ok'}, 'contributions': [], 'news': []}


@needs_db
def test_sincronizacion_entre_dispositivos_y_reporte_con_cartera_actual():
    from ontology.db import init_schema
    init_schema(retries=1)
    import server
    from core import portfolio_reports_api as api
    server.app.config['TESTING'] = True
    c = server.app.test_client()
    H = {'X-Khipu-Owner': 's' * 24}
    pf = [{'id': 'p9', 'name': 'Sync', 'cash': 50, 'startCash': 1000,
           'positions': [{'nodeId': 'Nvidia', 'shares': 2, 'avgPrice': 100}]}]
    assert c.put('/api/user-state', json={'key': 'kh_portfolios', 'value': pf, 'updated_at': '2026-10-01T00:00:00Z'},
                 headers=H).get_json()['ok']
    assert c.put('/api/user-state', json={'key': 'otra', 'value': 1}, headers=H).status_code == 400
    # el "teléfono" (misma llave) lo lee
    st = c.get('/api/user-state', headers=H).get_json()['state']
    assert st['kh_portfolios']['value'][0]['name'] == 'Sync'
    # una escritura más VIEJA no pisa la nueva
    r = c.put('/api/user-state', json={'key': 'kh_portfolios', 'value': [], 'updated_at': '2026-09-01T00:00:00Z'}, headers=H)
    assert r.status_code == 409 and r.get_json()['value'][0]['name'] == 'Sync'
    assert c.get('/api/user-state').status_code == 401
    import hashlib
    owner = hashlib.sha256(('s' * 24).encode()).hexdigest()
    cur = api.current_positions(owner, 'pf:p9')
    assert cur['positions'][0]['symbol'] == 'NVDA' and cur['positions'][0]['shares'] == 2 and cur['start_value'] == 1000
    seen = {}

    def build(pos, **k):
        seen['pos'] = pos
        return _fake_build(pos, **k)
    c.post('/api/portfolio-report/watch', json={'source_key': 'pf:p9', 'name': 'Sync', 'schedule': 'daily',
                                                'positions': [{'symbol': 'AMD', 'shares': 1}]}, headers=H)
    api.run_due(now=datetime(2026, 10, 9, 22, tzinfo=timezone.utc), build=build)
    assert seen['pos'][0]['symbol'] == 'NVDA'          # usa la cartera sincronizada de hoy, no la vieja
