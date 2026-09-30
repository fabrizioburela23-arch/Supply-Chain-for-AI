"""tests/test_space2.py — Space Monitor (core/space.py, /api/space2/*).

Launch Library 2 está bloqueada en CI/sandbox: la normalización se verifica
con payloads que reproducen la FORMA real de LL2 2.2.0 (mode=detailed:
latitudes como texto, vidURLs, mission.agencies…) y la red se sustituye
(monkeypatch de core.space._http_get_json). Nada toca la base de datos.
"""
import copy
from datetime import datetime, timezone

import pytest
from flask import Flask

import core.space as SP

NOW = 1_790_000_000.0          # 2026-09-21 aprox.


def iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def ll2_launch(lid, name, net, provider='SpaceX', provider_abbrev='SpX', status=(1, 'Go', 'Go for Launch'),
               lat='28.56194122', lon='-80.57735736', pad='Space Launch Complex 40',
               loc='Cape Canaveral SFS, FL, USA', mission='Starlink Group 10-5', orbit=('Low Earth Orbit', 'LEO'),
               agencies=None, vids=None, precision='Second', rocket='Falcon 9', manufacturer=None):
    return {
        'id': lid, 'url': f'https://ll.thespacedevs.com/2.2.0/launch/{lid}/', 'slug': lid, 'name': name,
        'status': {'id': status[0], 'name': status[2], 'abbrev': status[1], 'description': 'desc'},
        'last_updated': iso(NOW - 600), 'net': iso(net), 'net_precision': {'id': 0, 'name': precision, 'abbrev': 'SEC'},
        'window_end': iso(net + 3600), 'window_start': iso(net), 'probability': 90,
        'holdreason': '', 'failreason': '' if status[0] != 4 else 'Second stage anomaly', 'hashtag': None,
        'launch_service_provider': {'id': 121, 'url': 'x', 'name': provider, 'abbrev': provider_abbrev,
                                    'type': 'Commercial', 'country_code': 'USA'},
        'rocket': {'id': 8000, 'configuration': {'id': 164, 'name': rocket, 'family': 'Falcon', 'full_name': rocket + ' Block 5',
                                                 'variant': 'Block 5', 'manufacturer': manufacturer}},
        'mission': {'id': 7000, 'name': mission, 'description': 'A batch of satellites for the constellation.',
                    'type': 'Communications', 'orbit': {'id': 8, 'name': orbit[0], 'abbrev': orbit[1]},
                    'agencies': agencies or [], 'info_urls': [], 'vid_urls': []},
        'pad': {'id': 80, 'name': pad, 'latitude': lat, 'longitude': lon,
                'map_url': 'https://www.google.com/maps?q=28.56,-80.57', 'wiki_url': 'javascript:alert(1)',
                'location': {'id': 12, 'name': loc, 'country_code': 'USA'}, 'country_code': 'USA'},
        'webcast_live': False, 'image': 'https://img.example.org/f9.jpg',
        'vidURLs': vids if vids is not None else [
            {'priority': 10, 'source': 'youtube.com', 'publisher': 'SpaceX', 'title': 'Starlink Mission',
             'url': 'https://www.youtube.com/watch?v=abc'},
            {'priority': 1, 'source': 'x.com', 'title': 'Live', 'url': 'javascript:alert(1)'}],
        'infoURLs': [],
    }


UPCOMING = {'count': 5, 'results': [
    ll2_launch('u1', 'Falcon 9 Block 5 | Starlink Group 10-5', NOW + 2 * 3600),
    ll2_launch('u2', 'Electron | The Owl Spreads Its Wings', NOW + 3 * 86400, provider='Rocket Lab Ltd',
               provider_abbrev='RL', rocket='Electron', lat='-39.262833', lon='177.864469',
               pad='Rocket Lab Launch Complex 1A', loc='Rocket Lab Launch Complex 1, Mahia Peninsula, New Zealand',
               mission='The Owl Spreads Its Wings', orbit=('Sun-Synchronous Orbit', 'SSO'),
               agencies=[{'id': 1, 'name': 'Synspective', 'abbrev': 'SYN', 'type': 'Commercial'}], vids=[]),
    ll2_launch('u3', 'Falcon 9 Block 5 | Project Kuiper KF-04', NOW + 10 * 86400, mission='Project Kuiper KF-04',
               agencies=[{'id': 2, 'name': 'Amazon', 'abbrev': 'AMZN', 'type': 'Commercial'}]),
    ll2_launch('u4', 'Long March 5 | Mystery', NOW + 20 * 86400, provider='China Aerospace Science and Technology Corporation',
               provider_abbrev='CASC', rocket='Long March 5', lat=None, lon=None, pad='Unknown Pad',
               mission='Mystery', orbit=('Geostationary Transfer Orbit', 'GTO'), status=(2, 'TBD', 'To Be Determined'),
               precision='Month'),
    {'name': 'broken, no id'},
]}

PREVIOUS = {'count': 3, 'results': [
    ll2_launch('p1', 'Falcon 9 Block 5 | Starlink Group 9-9', NOW - 2 * 86400, status=(3, 'Success', 'Launch Successful')),
    ll2_launch('p2', 'Firefly Alpha | FLTA007', NOW - 12 * 86400, provider='Firefly Aerospace', provider_abbrev='FA',
               rocket='Alpha', status=(4, 'Failure', 'Launch Failure'), lat='34.632', lon='-120.611',
               pad='SLC-2W', loc='Vandenberg SFB, CA, USA', mission='FLTA007'),
    ll2_launch('p3', 'Old one', NOW - 60 * 86400, status=(3, 'Success', 'Launch Successful')),
]}


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    SP._reset_cache()
    monkeypatch.setattr(SP, '_now', lambda: NOW)

    def _no_net(*a, **k):
        raise AssertionError('red real no permitida en tests')
    monkeypatch.setattr(SP, '_http_get_json', _no_net)
    yield
    SP._reset_cache()


def fake_http(calls=None, fail=None):
    def f(url, params=None, timeout=None):
        if calls is not None:
            calls.append((url, dict(params or {})))
        if fail:
            return None, fail
        if '/launch/upcoming/' in url:
            return copy.deepcopy(UPCOMING), None
        if '/launch/previous/' in url:
            return copy.deepcopy(PREVIOUS), None
        return None, 'http:404'
    return f


def client():
    app = Flask(__name__)
    app.register_blueprint(SP.space_bp)
    return app.test_client()


# ── normalización ───────────────────────────────────────────────────────────
def test_normalize_launch_shape_and_safety():
    out = SP.normalize_payload(copy.deepcopy(UPCOMING))
    assert [l['id'] for l in out] == ['u1', 'u2', 'u3', 'u4']        # el roto se descarta
    l = out[0]
    assert l['pad']['lat'] == pytest.approx(28.56194122) and l['pad']['lon'] == pytest.approx(-80.57735736)
    assert l['pad']['wiki_url'] is None                                # javascript: fuera
    assert l['status']['kind'] == 'go' and l['status']['abbrev'] == 'Go'
    assert l['net'] == iso(NOW + 2 * 3600) and l['net_ts'] == NOW + 2 * 3600
    assert l['net_precision'] == 'Second'
    assert l['rocket']['name'] == 'Falcon 9' and l['provider']['name'] == 'SpaceX'
    assert l['mission']['orbit'] == {'name': 'Low Earth Orbit', 'abbrev': 'LEO'}
    assert [v['url'] for v in l['vid_urls']] == ['https://www.youtube.com/watch?v=abc']   # solo http(s)
    assert l['window_start'] and l['window_end']
    # sin coordenadas → lat/lon None (el cliente NO lo dibuja)
    l4 = out[3]
    assert l4['pad']['lat'] is None and l4['pad']['lon'] is None
    assert l4['status']['kind'] == 'tbd' and l4['net_precision'] == 'Month'


def test_normalize_bad_payload():
    with pytest.raises(ValueError):
        SP.normalize_payload({'detail': 'Request was throttled.'})
    assert SP.normalize_launch({'id': 'x', 'pad': {'latitude': '0', 'longitude': '0'}})['pad']['lat'] is None
    assert SP.normalize_launch({'id': 'x', 'pad': {'latitude': 'abc', 'longitude': '10'}})['pad']['lat'] is None
    assert SP.normalize_launch({'id': 'x', 'pad': {'latitude': 95, 'longitude': 10}})['pad']['lat'] is None
    # 2.3.0: vid_urls + status solo con abbrev
    r = SP.normalize_launch({'id': 'y', 'status': {'abbrev': 'In Flight'},
                             'vid_urls': [{'url': 'https://yt.example/x', 'priority': 2}]})
    assert r['status']['kind'] == 'inflight' and r['vid_urls'][0]['url'] == 'https://yt.example/x'


# ── emparejamiento con el grafo ─────────────────────────────────────────────
def test_graph_matching_roles():
    out = {l['id']: l for l in SP.normalize_payload(copy.deepcopy(UPCOMING))}
    g1 = {g['id']: g for g in out['u1']['graph']}
    assert 'SpaceX' in g1 and g1['SpaceX']['role'] == 'provider'        # proveedor gana a "Starlink"
    g2 = {g['id']: g for g in out['u2']['graph']}
    assert g2['RocketLab']['role'] == 'provider'                        # "Rocket Lab Ltd" → sin sufijo
    g3 = {g['id']: g for g in out['u3']['graph']}
    assert g3['Amazon']['role'] == 'customer' and g3['SpaceX']['role'] == 'provider'
    assert out['u4']['graph'] == []                                     # CASC no está en el grafo
    for g in out['u1']['graph']:
        assert set(g) >= {'id', 'label', 'role', 'method', 'nrs', 'ticker'}


def test_mission_keyword_is_labeled():
    g = SP.match_graph({'name': 'Some Launcher Nobody Knows'}, [], 'OneWeb #20', 'X | OneWeb #20')
    assert g and g[0]['id'] == 'Eutelsat' and g[0]['role'] == 'payload' and g[0]['method'] == 'mission_keyword'
    assert SP.match_graph(None, [], 'Nothing here', 'Nothing') == []


def test_resolve_org_fallbacks():
    assert SP.resolve_org('United Launch Alliance', 'ULA')['id'] == 'ULA'
    assert SP.resolve_org('Northrop Grumman Space Systems')['id'] == 'Northrop'   # sin cola genérica
    # un paréntesis calificativo NO se recorta ("iSpace (China)" ≠ ispace de Japón, ni "China")
    assert SP.resolve_org('iSpace (China)') is None
    assert SP.resolve_org('National Aeronautics and Space Administration', 'NASA') is None


# ── caché / stale / presupuesto ─────────────────────────────────────────────
def test_cache_single_fetch_and_ttl(monkeypatch):
    calls = []
    monkeypatch.setattr(SP, '_http_get_json', fake_http(calls))
    d1, s1 = SP.get_launches('upcoming')
    d2, s2 = SP.get_launches('upcoming')
    assert len(calls) == 1 and s1['ok'] and s2['ok'] and len(d1) == 4
    assert calls[0][1]['mode'] == 'detailed' and calls[0][1]['limit'] == SP.FETCH_LIMIT['upcoming']
    assert SP.TTL['upcoming'] >= 600 and SP.TTL['previous'] >= 600     # plan gratuito LL2
    monkeypatch.setattr(SP, '_now', lambda: NOW + SP.TTL['upcoming'] + 1)
    SP.get_launches('upcoming')
    assert len(calls) == 2


def test_stale_on_error_and_backoff(monkeypatch):
    monkeypatch.setattr(SP, '_http_get_json', fake_http())
    SP.get_launches('upcoming')
    calls = []
    monkeypatch.setattr(SP, '_http_get_json', fake_http(calls, fail='rate_limited'))
    monkeypatch.setattr(SP, '_now', lambda: NOW + SP.TTL['upcoming'] + 5)
    data, src = SP.get_launches('upcoming')
    assert len(calls) == 1 and len(data) == 4
    assert src['ok'] is False and src['stale'] is True and src['error_code'] == 'rate_limited'
    assert src['as_of'] == iso(NOW) and src['error_es'] and src['error_en']
    # en backoff: no se vuelve a consultar
    monkeypatch.setattr(SP, '_now', lambda: NOW + SP.TTL['upcoming'] + 60)
    data, src = SP.get_launches('upcoming')
    assert len(calls) == 1 and src['stale'] and len(data) == 4


def test_cold_error_no_invented_data(monkeypatch):
    monkeypatch.setattr(SP, '_http_get_json', fake_http(fail='timeout'))
    data, src = SP.get_launches('previous')
    assert data == [] and src['ok'] is False and src['stale'] is False and src['error_code'] == 'timeout'


def test_hourly_budget(monkeypatch):
    calls = []
    monkeypatch.setattr(SP, '_http_get_json', fake_http(calls, fail='http:500'))
    t = [NOW]
    monkeypatch.setattr(SP, '_now', lambda: t[0])
    for i in range(40):
        t[0] = NOW + i * (SP.ERROR_TTL + 1) / 4
        SP.get_launches('upcoming' if i % 2 else 'previous')
    assert len(calls) <= SP.HOURLY_BUDGET
    _, src = SP.get_launches('upcoming')
    assert src['ok'] is False


def test_pending_when_other_thread_fetching(monkeypatch):
    SP._FETCH_LOCKS['upcoming'].acquire()
    try:
        data, src = SP.get_launches('upcoming')
    finally:
        SP._FETCH_LOCKS['upcoming'].release()
    assert data == [] and src['pending'] is True and src['error_code'] == 'pending'


# ── resumen ────────────────────────────────────────────────────────────────
def test_summarize_counts_and_next():
    up = SP.normalize_payload(copy.deepcopy(UPCOMING))
    prev = SP.normalize_payload(copy.deepcopy(PREVIOUS))
    s = SP.summarize(up, prev, now=NOW)
    assert s['next']['id'] == 'u1'
    c = s['counts']
    assert c['upcoming_7d'] == 2 and c['upcoming_30d'] == 4
    assert c['previous_7d'] == 1 and c['previous_30d'] == 2
    assert not c['upcoming_7d_truncated']
    assert s['outcomes_30d'] == {'success': 1, 'failure': 1, 'partial': 0, 'other': 0}
    wk = {p['name']: p for p in s['by_provider']['week']}
    assert wk['SpaceX']['count'] == 1 and wk['SpaceX']['graph_id'] == 'SpaceX'
    mo = {p['name']: p['count'] for p in s['by_provider']['month']}
    assert mo['SpaceX'] == 2
    # la plataforma sin coordenadas no aparece
    assert all(p['lat'] is not None for p in s['pads'])
    assert {p['name'] for p in s['pads']} == {'Space Launch Complex 40', 'Rocket Lab Launch Complex 1A'}
    slc = [p for p in s['pads'] if p['name'] == 'Space Launch Complex 40'][0]
    assert slc['upcoming'] == 2 and slc['next_net'] == iso(NOW + 2 * 3600)
    ids = {x['id'] for x in s['graph']['companies']}
    assert {'SpaceX', 'RocketLab', 'Amazon'} <= ids
    assert s['graph']['launches_with_graph'] == 3 and s['graph']['upcoming_total'] == 4


def test_next_skips_final_and_old():
    up = SP.normalize_payload(copy.deepcopy(UPCOMING))
    up[0]['status']['kind'] = 'success'
    assert SP.next_launch(up, now=NOW)['id'] == 'u2'
    assert SP.next_launch(up, now=NOW + 40 * 86400) is None


# ── endpoints ──────────────────────────────────────────────────────────────
def test_endpoints(monkeypatch):
    monkeypatch.setattr(SP, '_http_get_json', fake_http())
    c = client()
    r = c.get('/api/space2/launches?window=upcoming&limit=2')
    assert r.status_code == 200
    j = r.get_json()
    assert j['window'] == 'upcoming' and j['count'] == 2 and [l['id'] for l in j['launches']] == ['u1', 'u2']
    assert j['source']['ok'] and j['source']['provider'].startswith('Launch Library 2')
    r = c.get('/api/space2/launches?window=previous')
    j = r.get_json()
    assert [l['id'] for l in j['launches']] == ['p1', 'p2', 'p3']            # más reciente primero
    r = c.get('/api/space2/summary')
    j = r.get_json()
    assert r.status_code == 200 and j['next']['id'] == 'u1'
    assert j['sources']['upcoming']['ok'] and j['sources']['previous']['ok']


def test_endpoint_validation():
    c = client()
    assert c.get('/api/space2/launches?window=next').status_code == 400
    r = c.get('/api/space2/launches?limit=0')
    assert r.status_code == 400 and r.get_json()['error_code'] == 'bad_limit'
    assert c.get('/api/space2/launches?limit=abc').status_code == 400


def test_endpoint_source_down(monkeypatch):
    monkeypatch.setattr(SP, '_http_get_json', fake_http(fail='conn:ll.thespacedevs.com'))
    j = client().get('/api/space2/summary').get_json()
    assert j['next'] is None and j['counts']['upcoming_30d'] == 0
    assert j['sources']['upcoming']['ok'] is False and j['sources']['upcoming']['error_code'] == 'no_connection'


def test_ll2_base_env(monkeypatch):
    monkeypatch.setenv('SPACE_LL2_BASE', 'https://lldev.thespacedevs.com/2.3.0/')
    calls = []
    monkeypatch.setattr(SP, '_http_get_json', fake_http(calls))
    SP.get_launches('upcoming')
    assert calls[0][0] == 'https://lldev.thespacedevs.com/2.3.0/launch/upcoming/'
