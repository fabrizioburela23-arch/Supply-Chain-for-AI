"""core/gdelt_events.py — conflicto/protestas/sanciones desde los archivos crudos de eventos de GDELT 2.0
(la API GEO fue retirada → las tres capas estaban "en pausa"). Sin red: lotes simulados."""
import io
import os
import sys
import zipfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import gdelt_events as GE  # noqa: E402
from core import world as W  # noqa: E402


def row(code, lat, lon, place, n_src=3, n_art=6, geo_type=4, url='https://news.example.com/a', gold=-10, actor='MIL', root='1'):
    r = [''] * 61
    r[12], r[25] = actor, root
    r[26], r[27], r[28] = code, code[:3], code[:2]
    r[30], r[32], r[33] = str(gold), str(n_src), str(n_art)
    r[51], r[52], r[53], r[56], r[57], r[60] = str(geo_type), place, 'UP', str(lat), str(lon), url
    return '\t'.join(r)


LAST = '20261005160000'
ROWS = [row('193', 49.99, 36.23, 'Kharkiv, Kharkivs\'ka Oblast\', Ukraine', url='https://a.com/1'),
        row('190', 49.98, 36.25, 'Kharkiv, Kharkivs\'ka Oblast\', Ukraine', n_art=10, url='https://b.com/2'),
        row('141', 48.85, 2.35, 'Paris, France', n_src=2, n_art=3, url='https://p.com/1'),
        row('141', 48.85, 2.35, 'Paris, France', n_src=2, n_art=3, url='https://p.com/2'),
        row('163', 35.69, 51.39, 'Tehran, Tehran, Iran', n_src=4, n_art=8),
        row('193', 10.0, 10.0, 'Ruido, Nigeria', n_src=1, n_art=1),      # una sola nota: se descarta
        row('042', 40.0, 40.0, 'Visita, Turkey'),                          # no es de ninguna capa
        row('190', 0, 0, 'sin lugar'),                                     # sin coordenadas: fuera
        row('193', 41.5, -81.7, 'Cleveland, Ohio, United States', actor='COP'),   # crimen común (sin actor armado): fuera
        row('190', 14.6, 120.98, 'Manila, Philippines', actor=''),         # "combatir delitos financieros": fuera
        row('190', 49.9, 36.2, 'Kharkiv', root='0'),                      # evento secundario de la nota: fuera
        row('190', 40.0, -4.0, 'Spain', geo_type=1, n_src=2),             # solo país, poca cobertura: fuera
        row('190', 46.9, -110.3, 'Montana, United States', n_src=2, n_art=10, url='https://one.com/x')]  # UNA sola nota: fuera


class _R:
    def __init__(self, status, text='', content=b''):
        self.status_code, self.text, self.content = status, text, content


def _zip(lines):
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w') as z:
        z.writestr('x.export.CSV', '\n'.join(lines))
    return b.getvalue()


def _fake_get(url, timeout=20):
    if url.endswith('lastupdate.txt'):
        return _R(200, f'1 a http://data.gdeltproject.org/gdeltv2/{LAST}.export.CSV.zip\n2 b http://x/{LAST}.mentions.CSV.zip')
    if LAST in url:
        return _R(200, content=_zip(ROWS))
    return _R(404)


def setup_function(_):
    GE._STORE.update(batches={}, latest=None, checked=0.0, errors=0)
    W._reset_cache()


def test_parse_filtra_ruido_y_clasifica_por_cameo():
    evs = GE.parse_export('\n'.join(ROWS), 0)
    assert sorted(e[0] for e in evs) == ['conflict', 'conflict', 'conflict', 'trade', 'unrest', 'unrest']
    assert GE.classify('15', '150', 1, {'MIL'}) is None and GE.classify('15', '150', 3, {'MIL'}) == 'conflict'
    assert GE.classify('19', '190', 9, {'COP'}) is None and GE.classify('14', '141', 2) == 'unrest'
    assert GE.severity(5, 3) < GE.severity(25, 10) < 100 and GE.severity(0, 0) == 15
    assert GE.severity(72, 40) < 85 and GE.severity(500, 100, days=7) < GE.severity(500, 100)   # un día completo NO satura en 100


def test_capas_en_vivo_agrupadas_con_fuentes(monkeypatch):
    monkeypatch.setenv('WORLD_GDELT_EVENTS', 'on')
    monkeypatch.setattr(GE, '_get', _fake_get)
    now = datetime(2026, 10, 5, 16, 5, tzinfo=timezone.utc).timestamp()
    monkeypatch.setattr(W, '_now', lambda: now)
    monkeypatch.setattr(GE.time, 'time', lambda: now)
    out = W.world_events(layers=['conflict', 'unrest', 'trade'], window='24h', wait=5)
    for lyr in ('conflict', 'unrest', 'trade'):
        assert out['sources'][lyr]['ok'] is True, (lyr, out['sources'][lyr])
        assert out['sources'][lyr]['coverage_hours'] == 2.0   # primer arranque: las últimas 2 h (8 lotes) and out['sources'][lyr]['press_signal']
    kh = [i for i in out['items'] if i['layer'] == 'conflict']
    assert len(kh) == 1                                           # dos eventos en Kharkiv → un punto; Montana (1 nota) fuera
    assert kh[0]['distinct_articles'] == 2
    k = kh[0]
    assert k['count'] == 16 and k['events'] == 2 and k['country_key'] == 'Ucrania'
    assert {a['url'] for a in k['articles']} == {'https://a.com/1', 'https://b.com/2'}
    assert k['title_es'].startswith('Combate') and 'Kharkiv' in k['title_es'] and k['time'].startswith('2026-10-05T16:00')
    assert any(i['layer'] == 'trade' and 'Embargo' in i['title_es'] for i in out['items'])
    assert out['sources']['conflict']['provider'].startswith('GDELT 2.0 Events')


def test_fuente_caida_dice_por_que(monkeypatch):
    monkeypatch.setenv('WORLD_GDELT_EVENTS', 'on')
    monkeypatch.setattr(GE, '_get', lambda url, timeout=20: _R(503))
    out = W.world_events(layers=['unrest'], window='24h', wait=5)
    s = out['sources']['unrest']
    assert s['ok'] is False and s['error_code'] in ('http_503', 'source_unavailable')


def test_relleno_en_segundo_plano_completa_24h(monkeypatch):
    """Tras cada despliegue la capa quedaba con '2 h' de historia: el relleno baja el resto sin bloquear."""
    monkeypatch.setenv('WORLD_GDELT_BACKFILL', 'on')
    monkeypatch.setattr(GE, '_get', _fake_get)
    monkeypatch.setattr(GE, 'BACKFILL_PAUSE', 0)
    now = datetime(2026, 10, 5, 16, 5, tzinfo=timezone.utc).timestamp()
    monkeypatch.setattr(GE.time, 'time', lambda: now)
    monkeypatch.setattr(GE.time, 'sleep', lambda s: None)
    assert GE.refresh() is None
    GE._BF['thread'].join(10)
    have, want = GE.coverage(86400, now=now)
    assert have == want == 24.0
