"""Informe de la simulación (2026-10-21): core/sim_report.build suma, SIN IA ni cifras inventadas, ticker/sector/país,
capitalización en vivo, valor en juego, cifras clave, sectores, países, TU cartera y metodología; engine/simreport.js lo
pinta (bilingüe, PDF, copiar)."""
import os

from core import sim_report as R

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = {'by_id': {'TSMC': {'label': 'TSMC', 'mkt': 'TSM', 'sector': 'fabricacion', 'country': 'Taiwan'},
                  'Nvidia': {'label': 'Nvidia', 'mkt': 'NVDA', 'sector': 'diseno', 'country': 'EEUU'},
                  'Intel': {'label': 'Intel', 'mkt': 'INTC', 'sector': 'fabricacion', 'country': 'EEUU'}}}
SIM = {'impacts': [{'id': 'TSMC', 'label': 'TSMC', 'pct': -12, 'channel': 'direct', 'path': 'TSMC'},
                   {'id': 'Nvidia', 'label': 'Nvidia', 'pct': -9, 'channel': 'customer', 'path': 'TSMC → Nvidia'},
                   {'id': 'Intel', 'label': 'Intel', 'pct': 6, 'channel': 'substitute', 'path': ''}],
       'model': 'claude-sonnet-5-5', 'rounds': [{}, {}], 'agents': [{}]}
CAPS = {'TSMC': {'mcap_b': 1000, 'change_pct': -1.0}, 'Nvidia': {'mcap_b': 4000}}


def test_rows_kpis_groups_and_method_only_from_inputs():
    r = R.build(SIM, 'es', caps=CAPS, caps_as_of='2026-10-21T14:30:00Z', snap=SNAP)
    t = {x['id']: x for x in r['rows']}
    assert t['TSMC']['ticker'] == 'TSM' and t['TSMC']['mcap_b'] == 1000 and t['TSMC']['value_at_stake_b'] == -120.0
    assert t['Intel']['mcap_b'] is None and t['Intel']['value_at_stake_b'] is None       # sin dato: vacío, nunca inventado
    k = r['kpis']
    assert (k['n_hit'], k['n_benefit'], k['n_sectors'], k['n_countries']) == (2, 1, 2, 2)
    assert k['worst']['label'] == 'TSMC' and k['mcap_hit_b'] == 5000 and k['value_loss_b'] == -480.0
    assert k['n_with_mcap'] == 2
    assert {s['key'] for s in r['by_sector']} == {'fabricacion', 'diseno'}
    assert 'TSMC' in r['headline'] and 'Intel' in r['headline']
    m = r['method']
    assert m['model'] == 'claude-sonnet-5-5' and m['rounds'] == 2 and m['caps_as_of'] == '2026-10-21T14:30:00Z'
    assert 'HIPOTÉTICO' in m['limits']


def test_portfolio_section_is_simple_labeled_arithmetic():
    pos = [{'id': 'Nvidia', 'symbol': 'NVDA', 'usd': 1000}, {'id': 'Apple', 'usd': 500}, {'id': 'x', 'usd': -3}]
    p = R.build(SIM, 'en', positions=pos, caps=CAPS, snap=SNAP)['portfolio']
    assert p['status'] == 'ok' and p['positions'][0]['est_usd'] == -90.0 and p['n_untouched'] == 1
    assert p['total_usd'] == 1500.0 and p['est_pct'] == -6.0 and 'not a price' in p['note']
    assert R.build(SIM, 'es', positions=[{'id': 'Apple', 'usd': 10}], caps=CAPS, snap=SNAP)['portfolio']['status'] == 'untouched'
    assert R.build(SIM, 'es', caps=CAPS, snap=SNAP)['portfolio']['status'] == 'no_positions'


def test_client_report_is_bilingual_and_wired():
    src = open(os.path.join(ROOT, 'engine', 'simreport.js'), encoding='utf-8').read()
    for es, en in (('Resumen ejecutivo', 'Executive summary'), ('Tu cartera en este escenario', 'Your portfolio in this scenario'),
                   ('Metodología y fuentes', 'Method and sources'), ('Copiar resumen', 'Copy summary'),
                   ('Valor en juego', 'Value at stake'), ('Por sector', 'By sector')):
        assert es in src and en in src
    cp = open(os.path.join(ROOT, 'engine', 'cockpit.js'), encoding='utf-8').read()
    assert 'KhipuSimReport.render' in cp and 'body.positions' in cp
    app = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    assert app.index('<script src="engine/simreport.js"') < app.index('<script src="engine/cockpit.js"')
    assert "'/engine/simreport.js'" in open(os.path.join(ROOT, 'sw.js'), encoding='utf-8').read()
    srv = open(os.path.join(ROOT, 'server.py'), encoding='utf-8').read()
    assert "sim_report.build(out, lang, positions=body.get('positions'))" in srv
