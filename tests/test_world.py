"""tests/test_world.py — World Monitor (core/world.py, /api/world/*).

Las fuentes externas (GDELT, USGS, EONET) están bloqueadas en CI/sandbox: los
parsers se verifican con payloads que reproducen la FORMA real de cada API, y
la red se sustituye (monkeypatch de core.world._http_get_json). Nada de estos
tests toca la base de datos (core.geosit se aísla de la ontología).
"""
import json
import os
import shutil
import subprocess
import time

import pytest
from flask import Flask

import core.geosit as geosit
import core.world as W

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOW = 1_790_000_000.0   # 2026-09-21 aprox.
_REAL_HTTP = W._http_get_json   # antes de que el fixture la sustituya


# ── fixtures con la forma real de cada fuente ───────────────────────────────
GDELT_PAYLOAD = {
    'type': 'FeatureCollection',
    'features': [
        {'type': 'Feature',
         'properties': {
             'name': 'Kyiv, Kyyiv, Misto, Ukraine', 'count': 57,
             'shareimage': 'https://example.org/img.jpg',
             'html': '<a href="https://news.example.org/a1" title="Missile strike hits Kyiv &amp; suburbs">'
                     'Missile strike hits Kyiv</a><BR><a href="https://news.example.org/a2" '
                     'title="Air raid alert">Air raid alert</a><BR>'},
         'geometry': {'type': 'Point', 'coordinates': [30.5167, 50.4333]}},
        {'type': 'Feature',
         'properties': {'name': 'Taipei, T\'ai-pei, Taiwan', 'count': 3,
                        'html': '<a href="javascript:alert(1)">bad</a>'},
         'geometry': {'type': 'Point', 'coordinates': [121.5319, 25.0478]}},
        {'type': 'Feature', 'properties': {'name': 'Broken'},
         'geometry': {'type': 'Point', 'coordinates': ['x', 'y']}},
        {'type': 'Feature', 'properties': {'name': 'Out of range', 'count': 9},
         'geometry': {'type': 'Point', 'coordinates': [500, 95]}},
        {'type': 'Feature', 'properties': {'name': 'Line', 'count': 9},
         'geometry': {'type': 'LineString', 'coordinates': [[0, 0], [1, 1]]}},
    ],
}

USGS_PAYLOAD = {
    'type': 'FeatureCollection',
    'metadata': {'generated': 1790000000000, 'title': 'USGS Magnitude 4.5+ Earthquakes, Past Week'},
    'features': [
        {'type': 'Feature', 'id': 'us7000abcd',
         'properties': {'mag': 6.4, 'place': '23 km E of Hualien City, Taiwan', 'time': int((NOW - 3600) * 1000),
                        'url': 'https://earthquake.usgs.gov/earthquakes/eventpage/us7000abcd',
                        'alert': 'yellow', 'tsunami': 0, 'sig': 630, 'title': 'M 6.4 - 23 km E of Hualien City, Taiwan'},
         'geometry': {'type': 'Point', 'coordinates': [121.83, 23.99, 12.3]}},
        {'type': 'Feature', 'id': 'us7000old1',
         'properties': {'mag': 4.6, 'place': '100 km S of Somewhere, Chile', 'time': int((NOW - 3 * 86400) * 1000),
                        'url': 'https://earthquake.usgs.gov/earthquakes/eventpage/us7000old1',
                        'alert': None, 'tsunami': 0, 'title': 'M 4.6 - 100 km S of Somewhere, Chile'},
         'geometry': {'type': 'Point', 'coordinates': [-71.0, -35.0, 40.0]}},
        {'type': 'Feature', 'id': 'bad', 'properties': {'mag': 5.0, 'time': 'nope'},
         'geometry': {'type': 'Point', 'coordinates': [0, 0]}},
    ],
}

EONET_PAYLOAD = {
    'title': 'EONET Events', 'link': 'https://eonet.gsfc.nasa.gov/api/v3/events',
    'events': [
        {'id': 'EONET_1', 'title': 'Typhoon Example', 'closed': None,
         'categories': [{'id': 'severeStorms', 'title': 'Severe Storms'}],
         'sources': [{'id': 'JTWC', 'url': 'https://www.metoc.navy.mil/jtwc/example'}],
         'geometry': [
             {'magnitudeValue': 60, 'magnitudeUnit': 'kts', 'date': '2026-09-19T00:00:00Z',
              'type': 'Point', 'coordinates': [130.0, 18.0]},
             {'magnitudeValue': 120, 'magnitudeUnit': 'kts', 'date': '2026-09-20T12:00:00Z',
              'type': 'Point', 'coordinates': [125.5, 21.2]}]},
        {'id': 'EONET_2', 'title': 'Big Fire, Oregon', 'closed': None,
         'categories': [{'id': 'wildfires', 'title': 'Wildfires'}],
         'sources': [{'id': 'InciWeb', 'url': 'https://inciweb.example.gov/2'}],
         'geometry': [{'magnitudeValue': 25000, 'magnitudeUnit': 'acres', 'date': '2026-09-18T00:00:00Z',
                       'type': 'Polygon', 'coordinates': [[[-122.0, 44.0], [-121.0, 44.0], [-121.0, 45.0],
                                                           [-122.0, 45.0], [-122.0, 44.0]]]}]},
        {'id': 'EONET_3', 'title': 'Volcano X', 'categories': [{'id': 'volcanoes', 'title': 'Volcanoes'}],
         'sources': [], 'link': 'https://eonet.gsfc.nasa.gov/api/v3/events/EONET_3',
         'geometry': [{'date': '2026-09-17T00:00:00Z', 'type': 'Point', 'coordinates': [14.99, 37.75]}]},
        {'id': 'EONET_4', 'title': 'No geometry', 'categories': [{'id': 'floods'}], 'geometry': []},
    ],
}

SITUATION = {
    'chokepoints': [
        {'id': 'taiwan_strait', 'es': 'Estrecho de Taiwán', 'en': 'Taiwan Strait', 'lat': 24.6, 'lon': 119.8,
         'base': 62, 'news': {'count': 40, 'tone': -5.0, 'age_min': 3}, 'factors': ['Tensión Taiwán'],
         'score': 90.0, 'why_es': 'x', 'why_en': 'x', 'sectors': ['fabricacion'],
         'affected': ['TSMC', 'Nvidia', 'NoExiste'], 'affected_dropped': 0},
        {'id': 'panama', 'es': 'Canal de Panamá', 'en': 'Panama Canal', 'lat': 9.1, 'lon': -79.7,
         'base': 38, 'news': None, 'factors': [], 'score': 38.0, 'why_es': 'y', 'why_en': 'y',
         'sectors': [], 'affected': [], 'affected_dropped': 0},
    ],
    'instability': [
        {'id': 'taiwan', 'es': 'Taiwán', 'en': 'Taiwan', 'lat': 23.7, 'lon': 121.0, 'country_key': 'Taiwan',
         'base': 62, 'news': None, 'factors': [], 'score': 62.0},
        {'id': 'nolatlon', 'es': 'X', 'en': 'X', 'base': 10, 'news': None, 'factors': [], 'score': 10.0},
    ],
    'fabs': [],
}


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """Sin red, sin BD, sin esperas de GDELT; caché limpia en cada test."""
    W._reset_cache()
    W._GDELT_LAST[0] = 0.0
    monkeypatch.setattr(W, 'GDELT_MIN_GAP', 0.0)
    monkeypatch.setattr(W, '_situation', lambda: SITUATION)
    monkeypatch.setattr(W, '_now', lambda: NOW)

    def _no_net(url, params=None, timeout=10):   # noqa: ARG001
        raise AssertionError('red real no permitida en tests: ' + url)
    monkeypatch.setattr(W, '_http_get_json', _no_net)
    yield
    W._reset_cache()


def _fake_http(counter=None, fail=()):
    def fake(url, params=None, timeout=10):   # noqa: ARG001
        if counter is not None:
            counter[url] = counter.get(url, 0) + 1
        if 'gdeltproject' in url:
            if 'gdelt' in fail:
                return None, 'http:503'
            return GDELT_PAYLOAD, None
        if 'usgs' in url:
            if 'usgs' in fail:
                raise RuntimeError('boom usgs')
            return USGS_PAYLOAD, None
        if 'eonet' in url:
            if 'eonet' in fail:
                return None, 'timeout'
            return EONET_PAYLOAD, None
        from tests.world_feed_fixtures import route
        feed = route(url)
        if feed is not None and 'feeds' in fail:
            return None, 'http:503'
        if feed is not None:
            return feed, None
        return None, 'unknown url'
    return fake


# ═══ 1. paridad de coordenadas con engine/geo_coords.js ═════════════════════
@pytest.mark.skipif(shutil.which('node') is None, reason='node no instalado')
def test_geo_coords_parity_with_js():
    script = r"""
const fs=require('fs'),vm=require('vm');
const ctx={window:{}};vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1]+'/engine/geo_coords.js','utf8'),ctx);
const G=ctx.window.GeoCoords;
const d=JSON.parse(fs.readFileSync(process.argv[1]+'/data/grafo_v0.json','utf8'));
const extra=[{id:'ZZ_1',country:'Estados Unidos (HQ Denver, CO)'},{id:'ZZ_2',country:'Canadá (Toronto, Ontario)'},
 {id:'ZZ_3',country:'RestoMundo',loc:'Chile'},{id:'ZZ_4',country:'Planeta Marte'},{id:'ñandú 🦙',country:'Japón'},
 {id:'ZZ_5',country:'Reino Unido / Noruega'},{id:'ZZ_6',loc:'Pekín, China'}];
const out={};d.nodes.concat(extra).forEach(n=>{out[n.id]=G.geoCoord(n);});
process.stdout.write(JSON.stringify(out));
"""
    res = subprocess.run(['node', '-e', script, ROOT], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    js = json.loads(res.stdout)
    snap = json.load(open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8'))
    extra = [{'id': 'ZZ_1', 'country': 'Estados Unidos (HQ Denver, CO)'},
             {'id': 'ZZ_2', 'country': 'Canadá (Toronto, Ontario)'},
             {'id': 'ZZ_3', 'country': 'RestoMundo', 'loc': 'Chile'}, {'id': 'ZZ_4', 'country': 'Planeta Marte'},
             {'id': 'ñandú 🦙', 'country': 'Japón'}, {'id': 'ZZ_5', 'country': 'Reino Unido / Noruega'},
             {'id': 'ZZ_6', 'loc': 'Pekín, China'}]
    nodes = snap['nodes'] + extra
    assert len(js) == len(nodes) >= 900          # 938 tras fusionar alias (G1b/G1d)
    for n in nodes:
        py = W.geo_coord(n)
        j = js[n['id']]
        assert abs(py['lat'] - j['lat']) < 1e-9 and abs(py['lng'] - j['lng']) < 1e-9, n['id']
        assert py['precision'] == j['precision'], n['id']
        assert py.get('country') == j.get('country'), n['id']
        assert py['label'] == j['label'], n['id']


def test_hash_and_jitter_match_js_semantics():
    # valores de referencia calculados con el JS (Math.imul / >> con signo)
    assert W._fnv('') == 2166136261
    assert W._fnv('a') == 3826002220           # FNV-1a 32 de "a"
    seed = 0xFFFFFFFF                            # ToInt32 → -1 → >>10 = -1 → %1000 = -1
    a, b = W._jitter(seed, 1.0)
    assert a == pytest.approx(((0xFFFFFFFF % 1000) / 1000) * 2 - 1)
    assert b == pytest.approx((-1 / 1000) * 2 - 1)


def test_country_key_and_place_country():
    assert W.country_key('Estados Unidos (HQ Denver, CO)') == 'EEUU'
    assert W.country_key('Japón') == 'Japon'
    assert W.country_key('United Arab Emirates') == 'EAU'
    assert W.country_key('Planeta Marte') is None
    assert W.place_country('Kyiv, Kyyiv, Misto, Ukraine') == 'Ucrania'
    assert W.place_country('23 km E of Hualien City, Taiwan') == 'Taiwan'
    assert W.place_country('10 km NE of Ridgecrest, CA') == 'EEUU'
    assert W.place_country('Gaza, Israel (general), Israel') == 'Israel'
    assert W.place_country('') is None


def test_graph_snapshot_nrs_matches_client_formula():
    g = W._graph()
    assert len(g['nodes']) >= 900
    tsmc = g['by_id']['TSMC']
    assert tsmc['precision'] == 'hq' and tsmc['country_key'] == 'Taiwan'
    assert 0 <= tsmc['nrs'] <= 100
    # misma fórmula que computeNRS (app.html): pre-IPO +10, 🔴 +5, TW/CN +10
    n = {'id': 'x', 'country': 'Taiwan', 'margin': 0.4, 'preipo': True, 'growth': '🔴 cae'}
    assert W.client_nrs(n, 4) == 25 + 10 + 0 + 15 + 10
    assert W.client_nrs({'id': 'y', 'country': 'EEUU', 'margin': -2.5}, 0) == 100   # sin acotar (como el cliente)
    assert W._js_round(2.5) == 3 and W._js_round(-2.5) == -2


# ═══ 2. parsers ══════════════════════════════════════════════════════════════
def test_parse_gdelt_geo_shape():
    items = W.parse_gdelt_geo(GDELT_PAYLOAD, 'conflict', '24h', now=NOW)
    assert [i['place'] for i in items] == ['Kyiv, Kyyiv, Misto, Ukraine', "Taipei, T'ai-pei, Taiwan"]
    kyiv = items[0]
    assert kyiv['layer'] == 'conflict' and kyiv['lat'] == 50.4333 and kyiv['lon'] == 30.5167
    assert kyiv['title'] == 'Missile strike hits Kyiv & suburbs'      # entidades HTML resueltas
    assert kyiv['url'] == 'https://news.example.org/a1'
    assert len(kyiv['articles']) == 2 and kyiv['country_key'] == 'Ucrania'
    assert kyiv['time_kind'] == 'window' and kyiv['source'] == 'GDELT'
    # GDELT no da hora del evento: 'time' vacío (no la hora de la consulta), fetched_at aparte
    assert kyiv['time'] is None and kyiv['ts'] is None and kyiv['fetched_at'].endswith('Z')
    assert kyiv['severity'] == W.gdelt_severity(57, '24h') and 0 < kyiv['severity'] <= 100
    taipei = items[1]
    assert taipei['url'] is None and taipei['title'].startswith('Taipei')   # javascript: descartado
    # id estable entre refrescos
    again = W.parse_gdelt_geo(GDELT_PAYLOAD, 'conflict', '24h', now=NOW + 999)
    assert again[0]['id'] == kyiv['id']
    with pytest.raises(ValueError):
        W.parse_gdelt_geo({'error': 'bad query'}, 'conflict')


def test_gdelt_severity_scales_per_day():
    assert W.gdelt_severity(0) == 15
    assert W.gdelt_severity(1) < W.gdelt_severity(10) < W.gdelt_severity(1000) == 100
    assert W.gdelt_severity(7, '7d') == W.gdelt_severity(1, '24h')   # por día


def test_parse_usgs_shape():
    items = W.parse_usgs(USGS_PAYLOAD)
    assert len(items) == 2                                   # el de 'time' inválido se descarta
    q = items[0]
    assert q['id'] == 'quakes:us7000abcd' and q['mag'] == 6.4 and q['depth_km'] == 12.3
    assert q['ts'] == pytest.approx(NOW - 3600) and q['time'].endswith('Z')
    assert q['severity'] == W.quake_severity(6.4, 'yellow', False) == 70
    assert q['country_key'] == 'Taiwan' and q['url'].startswith('https://earthquake.usgs.gov/')
    with pytest.raises(ValueError):
        W.parse_usgs([])


def test_quake_and_natural_severity_bounds():
    assert W.quake_severity(4.5) == 12 or W.quake_severity(4.5) == 13
    assert W.quake_severity(9.5, 'red', True) == 100
    assert W.quake_severity(None) == 0
    assert W.natural_severity('volcanoes') == 55
    assert W.natural_severity('severeStorms', 137, 'kts') == 96
    assert W.natural_severity('wildfires', 0, 'acres') == 30
    assert 30 < W.natural_severity('wildfires', 100000, 'acres') <= 70
    assert W.natural_severity('unknownCat') == 25


def test_parse_eonet_shape():
    items = {i['id']: i for i in W.parse_eonet(EONET_PAYLOAD)}
    assert set(items) == {'natural:EONET_1', 'natural:EONET_2', 'natural:EONET_3'}
    ty = items['natural:EONET_1']
    assert (ty['lat'], ty['lon']) == (21.2, 125.5)           # ÚLTIMA geometría
    assert ty['severity'] == 84 and ty['magnitude_unit'] == 'kts'
    assert ty['url'] == 'https://www.metoc.navy.mil/jtwc/example' and ty['time_kind'] == 'last_update'
    fire = items['natural:EONET_2']
    assert fire['lat'] == pytest.approx(44.5) and fire['lon'] == pytest.approx(-121.5)   # centroide (sin repetir el cierre)
    assert fire['category'] == 'wildfires'
    assert items['natural:EONET_3']['url'].endswith('EONET_3')   # sin sources → link del evento
    with pytest.raises(ValueError):
        W.parse_eonet({'events': 'x'})


# ═══ 3. caché, ventanas y aislamiento de errores ═══════════════════════════
def test_world_events_all_layers_and_contract(monkeypatch):
    monkeypatch.setattr(W, '_http_get_json', _fake_http())
    out = W.world_events(window='24h', wait=5)
    assert out['window'] == '24h' and set(out['sources']) == set(W.LIVE_LAYERS)
    for lyr, s in out['sources'].items():
        if lyr == 'outages':        # necesita CLOUDFLARE_RADAR_TOKEN (gratis): sin él lo dice, no inventa
            assert s['ok'] is False and s['error_code'] == 'needs_key' and 'Railway' in s['error_es']
            continue
        assert s['ok'] is True, lyr
        assert {'ok', 'count', 'as_of', 'provider'} <= set(s)
    for it in out['items']:
        assert {'id', 'layer', 'lat', 'lon', 'title', 'severity', 'time', 'source', 'url'} <= set(it)
    sev = [i['severity'] for i in out['items']]
    assert sev == sorted(sev, reverse=True)
    # chokepoints: ids afectados validados contra el grafo
    ck = next(i for i in out['items'] if i['id'] == 'chokepoints:taiwan_strait')
    assert ck['affected'] == ['TSMC', 'Nvidia'] and ck['severity'] == 90
    # instability sin coordenadas se omite
    assert not any(i['id'] == 'instability:nolatlon' for i in out['items'])


def test_quakes_window_filter(monkeypatch):
    monkeypatch.setattr(W, '_http_get_json', _fake_http())
    d24 = W.world_events(layers=['quakes'], window='24h', wait=5)
    d7 = W.world_events(layers=['quakes'], window='7d', wait=5)
    assert d24['sources']['quakes']['count'] == 1
    assert d7['sources']['quakes']['count'] == 2


def test_cache_ttl_and_single_fetch(monkeypatch):
    calls = {}
    monkeypatch.setattr(W, '_http_get_json', _fake_http(calls))
    W.world_events(layers=['quakes', 'natural'], wait=5)
    W.world_events(layers=['quakes', 'natural'], wait=5)
    W.world_events(layers=['quakes'], window='7d', wait=5)     # misma fuente → misma caché
    assert calls.get(W.USGS_URL) == 1 and calls.get(W.EONET_URL) == 1
    # vence el TTL de quakes (300 s) → se refresca en segundo plano
    monkeypatch.setattr(W, '_now', lambda: NOW + W.LAYER_TTL['quakes'] + 1)
    out = W.world_events(layers=['quakes'], wait=5)
    assert out['sources']['quakes']['ok']                      # sirve lo cacheado mientras tanto
    for th in list(W._INFLIGHT.values()):
        th.join(5)
    assert calls[W.USGS_URL] == 2


def test_error_isolation_and_stale(monkeypatch):
    monkeypatch.setattr(W, '_http_get_json', _fake_http(fail=('usgs', 'eonet')))
    out = W.world_events(window='24h', wait=5)
    s = out['sources']
    assert s['quakes']['ok'] is False and 'boom usgs' in s['quakes']['error']
    assert s['quakes']['error_code'] == 'internal' and 'boom usgs' in s['quakes']['error_es']
    assert s['natural']['ok'] is False and s['natural']['error_code'] == 'timeout'
    assert s['natural']['error_es'] == 'tiempo de espera agotado' and s['natural']['error_en'] == 'timed out'
    assert s['conflict']['ok'] is True and s['conflict']['count'] == 2      # las demás siguen
    assert s['chokepoints']['ok'] is True
    # stale: una capa que ya tenía datos y luego falla conserva los últimos
    W._reset_cache()
    monkeypatch.setattr(W, '_http_get_json', _fake_http())
    W.world_events(layers=['natural'], window='7d', wait=5)
    monkeypatch.setattr(W, '_http_get_json', _fake_http(fail=('eonet',)))
    monkeypatch.setattr(W, '_now', lambda: NOW + 10_000)
    W.world_events(layers=['natural'], window='7d', wait=5)
    for th in list(W._INFLIGHT.values()):
        th.join(5)
    out = W.world_events(layers=['natural'], window='7d', wait=5)
    assert out['sources']['natural']['ok'] is False and out['sources']['natural']['stale'] is True
    assert out['sources']['natural']['count'] == 3
    # cada ítem de una fuente caída lleva stale + as_of de los datos (no parecen de ahora)
    assert all(i['stale'] is True and i['as_of'] == W._iso(NOW) for i in out['items'])


def test_gdelt_error_and_pending(monkeypatch):
    monkeypatch.setattr(W, '_http_get_json', _fake_http(fail=('gdelt',)))
    out = W.world_events(layers=['conflict', 'trade'], wait=5)
    c = out['sources']['conflict']
    assert c['ok'] is False and c['error_code'] == 'http_503' and c['error'] == 'source returned HTTP 503'
    assert c['error_es'] == 'la fuente respondió HTTP 503'
    # capa fría con espera 0 → "pendiente", sin romper
    W._reset_cache()
    import threading
    gate = threading.Event()

    def slow(url, params=None, timeout=10):   # noqa: ARG001
        gate.wait(5)
        return USGS_PAYLOAD, None
    monkeypatch.setattr(W, '_http_get_json', slow)
    out = W.world_events(layers=['quakes'], wait=0)
    assert out['sources']['quakes']['pending'] is True and out['items'] == []
    gate.set()
    for th in list(W._INFLIGHT.values()):
        th.join(5)


def test_gdelt_throttle_spacing(monkeypatch):
    monkeypatch.setattr(W, '_now', time.time)
    monkeypatch.setattr(W, 'GDELT_MIN_GAP', 0.2)
    W._GDELT_LAST[0] = 0.0
    t0 = time.time()
    assert W.gdelt_throttle() and W.gdelt_throttle()
    assert time.time() - t0 >= 0.19
    assert W.gdelt_throttle(max_wait=0.01) is False           # no espera más de lo permitido


def test_http_get_json_edge_cases(monkeypatch):
    import requests as rq

    class R:
        def __init__(self, code, text):
            self.status_code, self.text = code, text
    fn = _REAL_HTTP
    monkeypatch.setattr(rq, 'get', lambda *a, **k: R(429, ''))
    assert fn('http://x')[1] == 'rate_limited'
    monkeypatch.setattr(rq, 'get', lambda *a, **k: R(503, ''))
    assert fn('http://x') == (None, 'http:503')
    monkeypatch.setattr(rq, 'get', lambda *a, **k: R(200, '<html>oops</html>'))
    assert fn('http://x')[1].startswith('nonjson:')
    monkeypatch.setattr(rq, 'get', lambda *a, **k: R(200, '{"features": []}'))   # JSON con content-type de texto
    assert fn('http://x') == ({'features': []}, None)

    def boom(*a, **k):
        raise rq.exceptions.Timeout()
    monkeypatch.setattr(rq, 'get', boom)
    assert fn('http://x') == (None, 'timeout')

    def noconn(*a, **k):
        raise rq.exceptions.ConnectionError('proxy said no')
    monkeypatch.setattr(rq, 'get', noconn)
    assert fn('https://api.gdeltproject.org/api/v2/geo/geo') == (None, 'conn:api.gdeltproject.org')


# ═══ 4. exposición (matemática de radio) y relevancia ══════════════════════
def test_haversine_known_distances():
    assert W.haversine_km(51.5074, -0.1278, 48.8566, 2.3522) == pytest.approx(343.6, abs=2)   # Londres–París
    assert W.haversine_km(25.03, 121.56, 24.80, 120.97) == pytest.approx(64, abs=5)           # Taipéi–Hsinchu
    assert W.haversine_km(0, 0, 0, 0) == 0


def test_exposure_radius_and_precision():
    ex = W.exposure(24.77, 120.99, 50)
    ids = [c['id'] for c in ex['companies']]
    assert 'TSMC' in ids and all(c['precision'] in ('hq', 'city') for c in ex['companies'])
    assert all(c['distance_km'] <= 50 for c in ex['companies'])
    assert [c['distance_km'] for c in ex['companies']] == sorted(c['distance_km'] for c in ex['companies'])
    assert any(f['company'] == 'TSMC' for f in ex['fabs'])
    small = W.exposure(24.77, 120.99, 1)
    assert small['near_count'] <= ex['near_count']
    # país compacto → también las registradas allí (aprox.)
    tw = W.exposure(23.99, 121.83, 60, country='Taiwan')
    assert tw['country_count'] > 0 and tw['index'] > W.exposure(23.99, 121.83, 60)['index']
    # país grande → un evento local NO expone a todo el país
    us = W.exposure(35.7, -117.5, 50, country='EEUU')
    assert us['country_count'] == 0
    # radio 0 + país (capa de inestabilidad) → sí, todo el país
    cn = W.exposure(34.0, 108.9, 0, country='China')
    assert cn['near_count'] == 0 and cn['country_count'] > 20
    # en medio del océano no hay nada
    sea = W.exposure(-40.0, -130.0, 300)
    assert sea['count'] == 0 and sea['index'] == 0


def test_exposure_affected_and_item_radius():
    ex = W.exposure(24.6, 119.8, 10, affected=['TSMC', 'Nvidia', 'NoExiste'])
    assert {c['id'] for c in ex['affected']} == {'TSMC', 'Nvidia'}
    assert W.item_radius_km({'layer': 'quakes', 'mag': 4.5}) == 60
    assert W.item_radius_km({'layer': 'quakes', 'mag': 7.5}) == 480
    assert W.item_radius_km({'layer': 'quakes', 'mag': 9.5}) == 800
    assert W.item_radius_km({'layer': 'natural', 'category': 'severeStorms'}) == 500
    assert W.item_radius_km({'layer': 'instability'}) == 0


def test_relevance_formula():
    assert W.relevance(100, 100) == 100
    assert W.relevance(0, 0) == 0
    assert W.relevance(60, 20) == round(0.55 * 60 + 0.45 * 20)


def test_brief_ranking(monkeypatch):
    monkeypatch.setattr(W, '_http_get_json', _fake_http(fail=('feeds',)))   # fuentes nuevas: tests propios
    b = W.brief(window='24h', n=5, wait=5)
    assert len(b['items']) == 5 and b['window'] == '24h'
    rel = [i['relevance'] for i in b['items']]
    assert rel == sorted(rel, reverse=True)
    top = b['items'][0]
    assert {'relevance', 'exposure', 'why_es', 'why_en'} <= set(top)
    assert top['id'] == 'chokepoints:taiwan_strait'          # severidad 90 + TSMC/Nvidia + fabs
    assert b['counts']['conflict'] == 2 and 'method_es' in b
    quake = next(i for i in W.brief(window='24h', n=25, wait=5)['items'] if i['layer'] == 'quakes')
    assert quake['exposure']['country_key'] == 'Taiwan' and quake['exposure']['count'] > 0
    assert 'Sismo' in quake['why_es'] and 'Earthquake' in quake['why_en']


# ═══ 5. geosit: datos reutilizables para el World Monitor ══════════════════
def test_geosit_situation_data_has_country_coords(monkeypatch):
    monkeypatch.setattr(geosit, '_ensure_warmer', lambda: None)
    monkeypatch.setattr(geosit, '_active_factor_matches', lambda: {})
    monkeypatch.setattr(geosit, '_known_ids', lambda: None)
    d = geosit.situation_data()
    assert d['chokepoints'] and d['instability'] and d['fabs']
    for c in d['instability']:
        assert -90 <= c['lat'] <= 90 and -180 <= c['lon'] <= 180
        assert c['country_key'] in W._COUNTRY, c['id']
    assert 'method_en' in d


# ═══ 6. endpoints (Flask mínimo con world_bp) ═════════════════════════════
@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(W, '_http_get_json', _fake_http())
    app = Flask(__name__)
    app.register_blueprint(W.world_bp)
    return app.test_client()


def test_endpoint_events(client):
    r = client.get('/api/world/events?window=24h')
    assert r.status_code == 200
    d = r.get_json()
    assert d['items'] and set(d['sources']) == set(W.LIVE_LAYERS)
    r = client.get('/api/world/events?layers=quakes,natural&window=7d')
    d = r.get_json()
    assert set(d['sources']) == {'quakes', 'natural'} and d['window'] == '7d'
    assert client.get('/api/world/events?window=1y').status_code == 400
    assert client.get('/api/world/events?layers=hack').status_code == 400


def test_endpoint_exposure(client):
    r = client.get('/api/world/exposure?lat=24.77&lon=120.99&radius_km=80&country=Taiwan&limit=5')
    assert r.status_code == 200
    d = r.get_json()
    assert d['near_count'] >= 1 and len(d['companies']) <= 5 and d['country_key'] == 'Taiwan'
    assert client.get('/api/world/exposure?lon=1').status_code == 400
    assert client.get('/api/world/exposure?lat=95&lon=1').status_code == 400
    assert client.get('/api/world/exposure?lat=abc&lon=1').status_code == 400
    assert client.get('/api/world/exposure?lat=1&lon=1&radius_km=99999').status_code == 400


def test_endpoint_brief_and_reference(client):
    r = client.get('/api/world/brief?window=24h&n=3')
    assert r.status_code == 200 and len(r.get_json()['items']) == 3
    assert client.get('/api/world/brief?n=abc').status_code == 400
    r = client.get('/api/world/reference')
    d = r.get_json()
    assert r.status_code == 200 and d['ref'] is True and d['live'] is False
    assert d['lanes'] and d['cables'] and d['landings'] and d['fabs']
    for coll in ('lanes', 'cables'):
        for x in d[coll]:
            assert x['es'] and x['en'] and len(x['path']) >= 2
            for lat, lon in x['path']:
                assert -90 <= lat <= 90 and -180 <= lon <= 180
    assert 'no en vivo' in d['note_es'] and 'not live' in d['note_en']


# ═══ 7. correcciones de revisión (fixer) ═══════════════════════════════════
def _real_situation(monkeypatch):
    """situation_data REAL de core.geosit (14 países, 9 estrechos) sin BD ni GDELT."""
    monkeypatch.setattr(geosit, '_ensure_warmer', lambda: None)
    monkeypatch.setattr(geosit, '_active_factor_matches', lambda: {})
    monkeypatch.setattr(geosit, '_known_ids', lambda: None)
    monkeypatch.setattr(W, '_situation', geosit.situation_data)


def test_instability_ranked_by_severity_not_company_count(monkeypatch):
    """Hallazgo 1: el conteo de empresas de TODO un país ya no infla la relevancia
    (antes EE.UU., score 28, quedaba arriba de Ucrania 78, Ormuz 55 e Israel 55)."""
    _real_situation(monkeypatch)
    monkeypatch.setattr(W, '_http_get_json', _fake_http(fail=('gdelt', 'usgs', 'eonet', 'feeds')))
    b = W.brief(window='24h', n=25, wait=5)
    ins = [i for i in b['items'] if i['layer'] == 'instability']
    assert len(ins) == 14
    sev = [i['severity'] for i in ins]
    assert sev == sorted(sev, reverse=True)                       # orden = severidad
    pos = {i['id']: k for k, i in enumerate(b['items'])}
    for higher in ('instability:ukraine', 'instability:israel', 'chokepoints:hormuz', 'instability:japan'):
        assert pos[higher] < pos['instability:usa'], higher
    us = next(i for i in ins if i['id'] == 'instability:usa')
    assert us['relevance'] == W.relevance(us['severity'], 0)
    # la exposición se sigue mostrando: % del grafo registrado en el país
    g = W._graph()
    assert us['exposure']['index_kind'] == 'share'
    assert us['exposure']['index'] == round(100 * len(g['by_country']['EEUU']) / len(g['nodes']))
    assert '% de tu grafo' in us['why_es'] and '% of your graph' in us['why_en']


def test_brief_reserves_slots_for_live_events(monkeypatch):
    """Hallazgo 1: un evento en vivo sin empresas cerca entra al top (cupo en vivo)."""
    _real_situation(monkeypatch)
    lonely = {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'id': 'us_sea', 'geometry': {'type': 'Point', 'coordinates': [-130.0, -40.0, 10.0]},
         'properties': {'mag': 5.3, 'place': 'southern East Pacific Rise', 'time': int((NOW - 3600) * 1000),
                        'url': 'https://earthquake.usgs.gov/x', 'alert': None, 'tsunami': 0}}]}

    def fake(url, params=None, timeout=10):   # noqa: ARG001
        if 'usgs' in url:
            return lonely, None
        return None, 'timeout'
    monkeypatch.setattr(W, '_http_get_json', fake)
    b = W.brief(window='24h', n=9, wait=5)
    assert len(b['items']) == 9
    q = next(i for i in b['items'] if i['id'] == 'quakes:us_sea')
    assert q['live_slot'] is True and q['exposure']['count'] == 0
    rel = [i['relevance'] for i in b['items']]
    assert rel == sorted(rel, reverse=True)
    # sin eventos vivos no hay cupo que llenar; con n mayor, el ítem cacheado no queda marcado
    b25 = W.brief(window='24h', n=25, wait=5)
    assert all('live_slot' not in i for i in b25['items'])


def test_gdelt_throttle_concurrent_respects_max_wait(monkeypatch):
    """Hallazgo 3: con varios hilos a la vez, max_wait se respeta (turnos reservados)."""
    import threading
    monkeypatch.setattr(W, '_now', time.time)
    monkeypatch.setattr(W, 'GDELT_MIN_GAP', 0.3)
    W._GDELT_LAST[0] = 0.0
    barrier = threading.Barrier(5)
    res, done = [], []

    def worker():
        barrier.wait()
        t0 = time.time()
        res.append(W.gdelt_throttle(max_wait=0.5))
        done.append(time.time() - t0)
    ths = [threading.Thread(target=worker) for _ in range(5)]
    for th in ths:
        th.start()
    for th in ths:
        th.join(5)
    assert sorted(res) == [False, False, False, True, True]       # turnos t y t+0.3; t+0.6 > 0.5
    assert max(done) < 0.9                                         # nadie espera 1, 2, 3… s


def test_natural_events_follow_window(monkeypatch):
    """Hallazgo 4: el filtro 24h/7d también aplica a NASA EONET (última actualización)."""
    payload = json.loads(json.dumps(EONET_PAYLOAD))
    payload['events'].append({'id': 'EONET_NEW', 'title': 'Fresh storm', 'categories': [{'id': 'severeStorms'}],
                              'sources': [], 'geometry': [{'date': W._iso(NOW - 7200), 'type': 'Point',
                                                           'coordinates': [140.0, 30.0]}]})
    monkeypatch.setattr(W, '_http_get_json', lambda url, params=None, timeout=10: (payload, None))
    d24 = W.world_events(layers=['natural'], window='24h', wait=5)
    d7 = W.world_events(layers=['natural'], window='7d', wait=5)
    assert [i['id'] for i in d24['items']] == ['natural:EONET_NEW']
    assert d7['sources']['natural']['count'] == 4


def test_stale_gdelt_marked_then_dropped(monkeypatch):
    """Hallazgo 9: datos GDELT de una fuente caída se marcan (stale + as_of) y,
    pasada la edad máxima, se descartan: nada de hotspots de hace días como '24h'."""
    monkeypatch.setattr(W, '_http_get_json', _fake_http())
    assert W.world_events(layers=['conflict'], wait=5)['sources']['conflict']['count'] == 2
    monkeypatch.setattr(W, '_http_get_json', _fake_http(fail=('gdelt',)))
    monkeypatch.setattr(W, '_now', lambda: NOW + 3600)
    W.world_events(layers=['conflict'], wait=5)
    for th in list(W._INFLIGHT.values()):
        th.join(5)
    out = W.world_events(layers=['conflict'], wait=5)
    src = out['sources']['conflict']
    assert src['stale'] is True and src['ok'] is False and src['count'] == 2
    assert all(i['stale'] is True and i['as_of'] == W._iso(NOW) and i['time'] is None for i in out['items'])
    # 5 días después, con la fuente todavía caída → se descartan
    monkeypatch.setattr(W, '_now', lambda: NOW + 5 * 86400)
    out = W.world_events(layers=['conflict'], wait=5)
    src = out['sources']['conflict']
    assert out['items'] == [] and src['count'] == 0 and src['expired_dropped'] == 2 and src['ok'] is False
    assert W.max_age_s('conflict', '24h') == 6 * 3600 and W.max_age_s('conflict', '7d') == 42 * 3600
    assert W.max_age_s('quakes', '24h') is None
    b = W.brief(window='24h', n=25, wait=5)
    assert not any(i['layer'] == 'conflict' for i in b['items'])


def test_old_ok_cache_waits_for_refresh(monkeypatch):
    """Hallazgo 9: un caché OK pero viejo (nadie consultó en días) no se sirve
    como actual: se espera al refresco y, si llega, se usan los datos nuevos."""
    calls = {}
    monkeypatch.setattr(W, '_http_get_json', _fake_http(calls))
    W.world_events(layers=['conflict'], wait=5)
    monkeypatch.setattr(W, '_now', lambda: NOW + 3 * 86400)
    out = W.world_events(layers=['conflict'], wait=5)
    assert out['sources']['conflict']['ok'] is True and out['sources']['conflict']['as_of'] == W._iso(NOW + 3 * 86400)
    assert out['sources']['conflict']['count'] == 2


def test_time_fields_are_not_fetch_time(monkeypatch):
    """Hallazgo 10: estrechos/países/GDELT no llevan la hora de consulta como 'time'."""
    monkeypatch.setattr(W, '_http_get_json', _fake_http())
    out = W.world_events(window='7d', wait=5)
    for it in out['items']:
        if it['time_kind'] in ('window', 'current'):
            assert it['time'] is None and it['fetched_at'], it['id']
        else:
            assert it['time'] and it['ts'], it['id']
    ck = next(i for i in out['items'] if i['id'] == 'chokepoints:taiwan_strait')
    assert ck['source_es'] == 'Khipu (curado) + GDELT' and ck['source_en'] == 'Khipu (curated) + GDELT'
    s = out['sources']['chokepoints']
    assert s['provider_es'].startswith('Khipu (curado)') and s['provider_en'].startswith('Khipu (curated)')


def test_err_info_is_bilingual():
    """Hallazgos 5/13: todo estado de fuente llega en es y en."""
    for code in ('timeout', 'conn:api.gdeltproject.org', 'rate_limited', 'http:503', 'nonjson:<html>',
                 'bad_payload:USGS', 'busy', 'pending', 'refreshing', 'no_data', 'exc:RuntimeError: x', 'raro'):
        e = W.err_info(code)
        assert e['error_code'] and e['error_es'] and e['error_en'] and e['error'] == e['error_en'], code
    assert W.err_info('conn:h')['error_es'] == 'sin conexión con h'
    assert W.err_info('conn:h')['error_en'] == 'no connection to h'
    assert 'GDELT' in W.err_info('busy')['error_en'] and 'ocupado' in W.err_info('busy')['error_es']


def test_busy_gdelt_retries_soon_and_is_labeled(monkeypatch):
    monkeypatch.setattr(W, 'gdelt_throttle', lambda max_wait=20.0: False)
    out = W.world_events(layers=['trade'], wait=5)
    s = out['sources']['trade']
    assert s['error_code'] == 'busy' and s['ok'] is False
    assert W._ttl('trade', W._CACHE[('trade', '24h')]) == W.BUSY_TTL


def test_parsers_drop_non_http_urls():
    """Hallazgos 8/11: USGS/EONET solo pasan enlaces http(s)."""
    usgs = json.loads(json.dumps(USGS_PAYLOAD))
    usgs['features'][0]['properties']['url'] = 'javascript:alert(document.cookie)'
    usgs['features'][1]['properties']['url'] = ' HTTPS://earthquake.usgs.gov/ok '
    q = W.parse_usgs(usgs)
    assert q[0]['url'] is None and q[1]['url'] == 'HTTPS://earthquake.usgs.gov/ok'
    eo = json.loads(json.dumps(EONET_PAYLOAD))
    eo['events'][0]['sources'][0]['url'] = 'data:text/html,<script>alert(1)</script>'
    eo['events'][0]['link'] = 'https://eonet.gsfc.nasa.gov/api/v3/events/EONET_1'
    eo['events'][2]['link'] = 'javascript:void(0)'
    items = {i['id']: i for i in W.parse_eonet(eo)}
    assert items['natural:EONET_1']['url'] == 'https://eonet.gsfc.nasa.gov/api/v3/events/EONET_1'
    assert items['natural:EONET_3']['url'] is None
    assert W._safe_url(None) is None and W._safe_url('ftp://x') is None


def test_exposure_country_share_and_saturation():
    g = W._graph()
    cn = W.exposure(34.0, 108.9, 0, country='China', limit=25)
    assert cn['index_kind'] == 'share' and cn['index'] == round(100 * len(g['by_country']['China']) / len(g['nodes']))
    assert cn['country_count'] == len(g['by_country']['China']) and len(cn['same_country']) == 25
    # evento local en país compacto sin empresas cerca: el "mismo país" satura (≤ 31)
    jp = W.exposure(43.0, 147.5, 30, country='Japon')
    assert jp['near_count'] == 0 and jp['country_count'] > 40 and jp['index_kind'] == 'proximity'
    assert jp['index'] <= round(100 * (1 - __import__('math').exp(-W.COUNTRY_W_MAX / 8)))


def test_exposure_endpoint_accepts_affected_like_brief(client, monkeypatch):
    """Hallazgos 2/14: el índice de un estrecho es el mismo desde el brief o
    desde /api/world/exposure (que ahora acepta los dependientes curados)."""
    _real_situation(monkeypatch)
    b = W.brief(window='24h', n=25, wait=5)
    for it in [i for i in b['items'] if i['layer'] == 'chokepoints']:
        q = (f"/api/world/exposure?lat={it['lat']}&lon={it['lon']}&radius_km={W.item_radius_km(it)}"
             f"&limit=25&affected={','.join(it['affected'])}")
        d = client.get(q).get_json()
        assert d['index'] == it['exposure']['index'], it['id']
    r = client.get('/api/world/exposure?lat=12.6&lon=43.3&radius_km=600&affected=' + ','.join(['x'] * 50))
    assert r.status_code == 200 and r.get_json()['affected_count'] == 0


def test_endpoint_errors_are_bilingual(client):
    d = client.get('/api/world/events?window=1y').get_json()
    assert d['error_code'] == 'bad_window' and d['error_es'] and d['error_en']
    d = client.get('/api/world/exposure?lat=abc&lon=1').get_json()
    assert d['error_code'] == 'bad_params' and 'inválidos' in d['error_es'] and 'invalid' in d['error_en']


def test_hq_coordinates_fixed():
    """Hallazgo 15: AST SpaceMobile en Midland, TX (antes ~470 km al este)."""
    g = W._graph()
    ast = g['by_id']['AST_SpaceMobile']
    assert W.haversine_km(ast['lat'], ast['lng'], 31.997, -102.078) < 15
    rk = g['by_id']['RocketLab']
    assert W.haversine_km(rk['lat'], rk['lng'], 33.77, -118.19) < 20       # Long Beach (sede)
