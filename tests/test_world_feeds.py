"""core/world_feeds.py — fuentes OFICIALES nuevas del World Monitor (2026-10-05, "más info, pero fiable").

Sin red: payloads con la forma real de FMI PortWatch, Federal Register (BIS/OFAC) y GDACS."""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import world as W  # noqa: E402
from core import world_feeds as F  # noqa: E402
from tests.world_feed_fixtures import FEDREG_PAYLOAD, GDACS_PAYLOAD, PORTWATCH_PAYLOAD, route  # noqa: E402


def _fake(fail=()):
    def fake(url, params=None, timeout=10):  # noqa: ARG001
        for k in fail:
            if k in url:
                return None, 'http:404' if k != 'gdacs' else 'http:500'
        d = route(url)
        return (d, None) if d is not None else (None, 'http:503')
    return fake


def setup_function(_):
    W._reset_cache()


def test_portwatch_caida_medida_y_estrechos_del_grafo():
    items = F.parse_portwatch([f['attributes'] for f in PORTWATCH_PAYLOAD['features']], {'suez': ['Nvidia']})
    suez = next(i for i in items if i['id'] == 'shipping:suez')
    assert suez['change_pct'] == -50.0 and suez['transits_7d_avg'] == 30 and suez['transits_base_avg'] == 60
    assert suez['severity'] == 80 and suez['affected'] == ['Nvidia'] and suez['official']
    assert suez['time'].startswith('2026-09-28') and 'portwatch' in suez['url']
    assert '▼ 50 %' in suez['title_es'] and '▼ 50%' in suez['title_en']
    mal = next(i for i in items if i['id'] == 'shipping:malacca')
    assert abs(mal['change_pct']) < 2 and mal['severity'] == 0          # estable = sin alarma
    assert F.shipping_severity(10) == 0 and F.shipping_severity(-25) == 40 and F.shipping_severity(-90) == 100


def test_federal_register_bis_ofac_pais_y_empresas():
    now = datetime(2026, 10, 1, tzinfo=timezone.utc).timestamp()
    feed = F.parse_fedreg(FEDREG_PAYLOAD, now=now)
    ent = next(i for i in feed if i['id'] == 'policy:2026-19001')
    assert ent['agency'] == 'BIS' and ent['target_country'] == 'China' and ent['lat'] is not None
    assert ent['country_key'] is None          # la regla NO expone a todas las empresas del país, solo a las nombradas
    assert any(c['id'] == 'SMIC' for c in ent['companies'])                 # empresa del grafo nombrada
    assert ent['severity'] >= 80 and ent['severity_kind'] == 'keyword_estimate'
    ofac = next(i for i in feed if i['id'] == 'policy:2026-19002')
    assert ofac['agency'] == 'OFAC' and ofac['target_country'] == 'Rusia'
    trivial = next(i for i in feed if i['id'] == 'policy:2026-19003')
    assert trivial.get('lat') is None and trivial['severity'] < 40          # sin país: solo en la lista
    assert [i['id'] for i in feed][0] == 'policy:2026-19001'                 # más reciente primero


def test_gdacs_solo_naranja_y_roja():
    items = F.parse_gdacs(GDACS_PAYLOAD)
    assert len(items) == 1
    t = items[0]
    assert t['alert'] == 'red' and t['severity'] == 90 and t['country_key'] == 'Taiwan'
    assert 'Super Typhoon' in t['severity_text'] and t['url'].startswith('https://www.gdacs.org/report')


def test_world_events_incluye_las_capas_nuevas_con_estado(monkeypatch):
    monkeypatch.setattr(W, '_http_get_json', _fake())
    monkeypatch.setattr(F, '_ref_affected', lambda: {'suez': ['Nvidia']})
    out = W.world_events(layers=['shipping', 'policy', 'disasters'], window='7d', wait=5)
    for lyr in ('shipping', 'policy', 'disasters'):
        assert out['sources'][lyr]['ok'] is True, lyr
    layers = {i['layer'] for i in out['items']}
    assert layers == {'shipping', 'policy', 'disasters'}
    assert out['sources']['policy']['provider'].startswith('US Federal Register')
    pol = F.policy_feed()
    assert len(pol['items']) == 3                                            # la lista incluye los sin país


def test_fuente_caida_lo_dice_y_no_tumba_a_las_demas(monkeypatch):
    monkeypatch.setattr(W, '_http_get_json', _fake(fail=('arcgis',)))
    for _ in range(W.SOURCE_DOWN_AFTER):
        W._reset_cache.__wrapped__() if hasattr(W._reset_cache, '__wrapped__') else None
        with W._LOCK:
            W._CACHE.clear()
        W.world_events(layers=['shipping', 'disasters'], window='7d', wait=5)
    out = W.world_events(layers=['shipping', 'disasters'], window='7d', wait=5)
    s = out['sources']['shipping']
    assert s['ok'] is False and s['error_code'] in ('source_unavailable', 'http_404')
    assert 'IMF PortWatch' in s['error_es'] or 'HTTP 404' in s['error_es']
    assert out['sources']['disasters']['ok'] is True


def test_gdacs_404_es_cero_alertas_no_caida(monkeypatch):
    monkeypatch.setattr(W, '_http_get_json', lambda url, params=None, timeout=10: (None, 'http:404'))
    items, err = F.fetch_disasters('7d')
    assert items == [] and err is None


def test_honestidad_con_datos_reales_de_produccion():
    """Lo visto en producción (2026-10-05): Kerch con 0 buques no es '−100 % seguro', las licencias
    generales de la OFAC no pesan como una sanción nueva y las sequías de 29 países no ocupan media pantalla."""
    from datetime import timedelta
    last = datetime(2026, 9, 27, tzinfo=timezone.utc)
    rows = [{'date': (last - timedelta(days=i)).strftime('%Y-%m-%d'), 'portname': 'Kerch Strait',
             'n_total': 0 if i < 7 else 12} for i in range(100)]
    k = F.parse_portwatch(rows)[0]
    assert k['data_caveat'] == 'no_ships_recorded' and k['severity'] == 70 and '0 buques' in k['title_es']
    now = datetime(2026, 10, 1, tzinfo=timezone.utc).timestamp()
    gl = {'results': [{'title': 'Publication of Venezuela Sanctions Regulations Web General Licenses 52, 53',
                       'type': 'Rule', 'document_number': 'x1', 'publication_date': '2026-09-30',
                       'agencies': [{'slug': 'foreign-assets-control-office'}]}]}
    assert F.parse_fedreg(gl, now=now)[0]['severity'] < 50
    big = {'features': [{'geometry': {'coordinates': [13.7, 48.7]}, 'properties': {
        'eventtype': 'DR', 'eventid': 9, 'alertlevel': 'Orange', 'name': '',
        'country': 'Austria, Belgium, Belarus, Switzerland, Germany, Spain', 'todate': '2026-10-05T05:57:07'}}]}
    d = F.parse_gdacs(big)[0]
    assert len(d['title_es']) < 90 and '6 países' in d['title_es'] and d['place'].endswith('+3')
