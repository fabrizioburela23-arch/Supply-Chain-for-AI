"""tests/test_space_satellites.py — «¿por qué la del espacio ya no tiene los satélites?» (2026-10-13).

Causas reproducidas (CelesTrak no es alcanzable desde CI: la red se simula con
requests.get parcheado, como en producción cuando CelesTrak bloquea la IP):

1. /api/space/tle pedía los 11 grupos EN SERIE (12 s cada uno) y no paraba ante
   un error: con CelesTrak colgado/bloqueado → ~132 s sin satélites, y cada visita
   (y el texto de Khipu) volvía a descargarlo todo — lo que hace que CelesTrak
   bloquee. Ahora: core/celestrak.py (copia por grupo, pausa ante bloqueo, ronda
   ≤ DEADLINE_S) y el respaldo de REFERENCIA llega enseguida y marcado.
2. La regla CSS global '.sm{min-height:520px;…}' del Space Monitor también vestía
   el chip de saldo del OS (<span class="v sm">): una caja oscura de 520 px tapaba
   el globo y sus satélites.
3. En la ventana angosta del OS los satélites medían ~1,5 px (como las estrellas).
4. Un fallo del servidor (429/503) dejaba el globo sin satélites hasta recargar.
"""
import os
import re
import sys

import pytest
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ISS = ('ISS (ZARYA)',
       '1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9994',
       '2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391428603')


def _tle_text(group, n=5):
    lines = []
    for k in range(n):
        lines += [f'{group.upper()}-{k}', ISS[1], ISS[2]]
    return '\n'.join(lines) + '\n'


class _R:
    def __init__(self, code, text):
        self.status_code = code
        self.ok = 200 <= code < 300
        self.text = text
        self.content = text.encode()


@pytest.fixture
def srv():
    import server
    try:
        server.cache.clear()
    except Exception:  # noqa: BLE001
        pass
    ct = sys.modules.get('core.celestrak')
    if ct is not None:
        ct.reset()
    server.app.config['TESTING'] = True
    yield server
    if ct is not None:
        ct.reset()
    try:
        server.cache.clear()
    except Exception:  # noqa: BLE001
        pass


def _patch(monkeypatch, fn):
    calls = []

    def fake(url, *a, **k):
        if 'celestrak' in str(url):
            calls.append(str(url))
            return fn(str(url))
        raise requests.ConnectionError('sin red en tests')
    monkeypatch.setattr(requests, 'get', fake)
    return calls


def _get(server, ip):
    return server.app.test_client().get('/api/space/tle', headers={'X-Forwarded-For': ip})


def test_celestrak_bloqueado_responde_ya_con_referencia_y_no_insiste(srv, monkeypatch):
    """Cortafuegos de CelesTrak (paquetes descartados = tiempo agotado): antes 11 esperas
    seguidas (~132 s sin satélites) y lo mismo en CADA visita."""
    def hang(url):
        raise requests.ConnectTimeout('timed out')
    calls = _patch(monkeypatch, hang)
    r = _get(srv, '10.9.0.1')
    assert r.status_code == 200
    d = r.get_json()
    assert d['source'] == 'fallback'                       # órbitas de REFERENCIA, dichas como tales
    assert len(d['sats']) > 0                               # el globo SIEMPRE tiene qué dibujar
    assert len(calls) == 1, f'insistió {len(calls)} veces con CelesTrak bloqueado'
    assert r.headers.get('Cache-Control') == 'no-store'
    # la segunda visita no vuelve a golpear a CelesTrak (pausa)
    r2 = _get(srv, '10.9.0.1')
    assert r2.get_json()['source'] == 'fallback'
    assert len(calls) == 1
    # el texto de Khipu tampoco descarga por su cuenta
    srv._space_constellations()
    assert len(calls) == 1


def test_copia_por_grupo_403_sin_cambios_y_copia_vieja_honesta(srv, monkeypatch):
    import core.celestrak as CT
    t = [1_800_000_000.0]
    monkeypatch.setattr(CT, '_now', lambda: t[0])
    mode = {'m': 'ok'}

    def upstream(url):
        g = re.search(r'GROUP=([^&]+)', url).group(1)
        if mode['m'] == 'ok':
            return _R(200, _tle_text(g))
        if mode['m'] == 'unchanged':
            return _R(403, f'GP data has not updated since your last successful download of GROUP={g}')
        return _R(403, 'Forbidden')                         # bloqueo
    calls = _patch(monkeypatch, upstream)

    d = _get(srv, '10.9.0.2').get_json()
    assert d['source'] == 'celestrak' and len(calls) == len(CT.GROUPS)
    assert all(c['count'] == 5 and c.get('as_of') for c in d['constellations'])
    assert not d['stale']

    # misma copia para el texto de Khipu y para otra visita: CERO descargas nuevas
    cons = srv._space_constellations()
    assert all(live for _l, _n, live in cons) and len(calls) == len(CT.GROUPS)
    _get(srv, '10.9.0.2')
    assert len(calls) == len(CT.GROUPS)

    # +3 h: CelesTrak dice «sin cambios» (403) → la copia sigue vigente, sin error ni «caída»
    t[0] += 3 * 3600
    mode['m'] = 'unchanged'
    d = _get(srv, '10.9.0.2').get_json()
    assert d['source'] == 'celestrak' and not any(c.get('error') for c in d['constellations'])
    assert not d['stale']

    # +7 h más con CelesTrak BLOQUEANDO: se para al primer no-200 y se sirve la copia real marcada vieja
    t[0] += 7 * 3600
    mode['m'] = 'blocked'
    n0 = len(calls)
    r = _get(srv, '10.9.0.2')
    d = r.get_json()
    assert len(calls) == n0 + 1
    assert d['source'] == 'celestrak' and d['stale'] is True
    assert all(c.get('stale') for c in d['constellations'])
    assert sum(c['count'] for c in d['constellations']) == 5 * len(CT.GROUPS)
    assert r.headers.get('Cache-Control') == 'no-store'

    # +8 días: la copia ya no se usa → referencia honesta
    t[0] += 8 * 86400
    d = _get(srv, '10.9.0.2').get_json()
    assert d['source'] == 'fallback' and d.get('reason')


def test_grupo_retirado_no_tumba_a_los_demas(srv, monkeypatch):
    def upstream(url):
        g = re.search(r'GROUP=([^&]+)', url).group(1)
        return _R(404, 'No GP data found') if g == 'spire' else _R(200, _tle_text(g, 3))
    _patch(monkeypatch, upstream)
    d = _get(srv, '10.9.0.3').get_json()
    assert d['source'] == 'celestrak'
    bad = [c for c in d['constellations'] if c.get('error')]
    assert [c['name'] for c in bad] == ['Spire Global']
    assert d['rendered'] == 3 * 10


def _read(p):
    with open(os.path.join(ROOT, p), encoding='utf-8') as f:
        return f.read()


def test_css_del_space_monitor_no_viste_al_chip_del_os():
    js = _read('engine/spacemonitor.js')
    assert "'.sm{" not in js, "regla '.sm{…}' global: también estira el chip <span class=\"v sm\"> del OS"
    assert "'#sm.sm{position:relative" in js
    assert "classList.toggle('sm'" in _read('engine/cockpit.js')   # el choque existe: por eso #sm


def test_satelites_legibles_y_reintento():
    js = _read('engine/spacemonitor.js')
    g = _read('engine/globe.js')
    assert re.search(r'SAT_OPTS\s*=\s*\{[^}]*minPx:\s*\d', js)
    assert '_satMinSize()' in g and 'minPx * this._dist / (h / 2)' in g
    body = js[js.index('function loadTLE()'):js.index('function later(')]
    assert 'later(loadTLE' in body and "'reintentando…', 'retrying…'" in body
    assert 'if (!S.tle) { S._tleTries = 0; loadTLE(); }' in js     # al reabrir la ventana
    assert "L('copia', 'cached')" in js
    # aviso honesto SOBRE el globo (en la ventana angosta del OS los paneles van en hojas ocultas)
    note = js[js.index('function renderSatNote()'):]
    note = note[:note.index('\n  }\n')]
    assert "'🛰 Órbitas de REFERENCIA, no en vivo: CelesTrak no responde', '🛰 REFERENCE orbits, not live: CelesTrak unreachable'" in note
    assert "'🛰 Satélites reales, copia del ', '🛰 Real satellites, copy from '" in note
    assert 'id="sm-satnote"' in js
