"""core/gdelt_events.py — conflicto / protestas / sanciones EN VIVO desde la base de
EVENTOS de GDELT 2.0 (archivos crudos cada 15 minutos, públicos y sin clave).

Por qué (2026-10-05): la API GDELT GEO 2.0 que alimentaba esas tres capas fue
RETIRADA (HTTP 404) y la pestaña Geopolítica mostraba "en pausa". Los archivos
crudos de eventos siguen publicándose:

    http://data.gdeltproject.org/gdeltv2/lastupdate.txt   → el último lote
    http://data.gdeltproject.org/gdeltv2/YYYYMMDDHHMMSS.export.CSV.zip

Cada lote trae ~1-3 mil eventos codificados por máquina (CAMEO) desde noticias
de todo el mundo, CON coordenadas del lugar de la acción. Para que sea FIABLE:
  · solo eventos con ≥ 2 fuentes distintas o ≥ 5 artículos (filtra ruido de una
    sola nota),
  · se agrupan por lugar (~10 km) y se cuenta la cobertura (artículos),
  · severidad = intensidad de cobertura (misma escala que antes): mide ATENCIÓN
    MEDIÁTICA, no víctimas — la UI lo dice,
  · cada punto trae las URLs de las notas originales,
  · la cobertura real (cuántas horas hay cargadas) va en el estado de la capa.

Capas (códigos CAMEO, raíz o base):
  conflict → 18 asalto · 19 combate · 20 violencia masiva (+ 15 despliegue de fuerza con ≥ 3 fuentes)
  unrest   → 14 protestas
  trade    → 163 imponer embargo / boicot / sanciones
Memoria: se guardan solo los eventos filtrados de los últimos 7 días (compactos).
Descarga incremental: como mucho MAX_PER_REFRESH lotes por refresco (los más
nuevos primero); el resto de la ventana se completa en refrescos siguientes.
"""
import csv
import io
import logging
import os
import threading
import time
import zipfile
from datetime import datetime, timedelta, timezone

import requests

log = logging.getLogger('world')

BASE = 'http://data.gdeltproject.org/gdeltv2/'
LASTUPDATE = BASE + 'lastupdate.txt'
KEEP_S = 7 * 86400
MAX_PER_REFRESH = 16
STEP = timedelta(minutes=15)
LAYERS = ('conflict', 'unrest', 'trade')

_STORE = {'batches': {}, 'latest': None, 'checked': 0.0, 'errors': 0}
_LOCK = threading.Lock()


def _base():
    return (os.environ.get('WORLD_GDELT_EVENTS_BASE') or BASE).rstrip('/') + '/'


def classify(root, base, n_sources):
    """Código CAMEO → capa (o None)."""
    if root in ('18', '19', '20'):
        return 'conflict'
    if root == '15' and n_sources >= 3:
        return 'conflict'
    if root == '14':
        return 'unrest'
    if base == '163':
        return 'trade'
    return None


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _i(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def parse_export(text, batch_ts):
    """CSV (tab) de 61 columnas → eventos compactos filtrados."""
    out = []
    for row in csv.reader(io.StringIO(text), delimiter='\t'):
        if len(row) < 61:
            continue
        n_src, n_art = _i(row[32]), _i(row[33])
        if n_src < 2 and n_art < 5:
            continue
        layer = classify(row[28], row[27], n_src)
        if not layer:
            continue
        lat, lon = _f(row[56]), _f(row[57])
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
            continue
        out.append((layer, round(lat, 3), round(lon, 3), row[52][:120], row[53][:2], _i(row[51]),
                    n_art, n_src, row[60][:400], batch_ts, row[26], _f(row[30])))
    return out


def _ts_of(name):
    try:
        return datetime.strptime(name, '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _get(url, timeout=20):
    return requests.get(url, timeout=timeout, headers={'User-Agent': 'KhipuFinance/1.0 (+world-monitor)'})


def _latest():
    r = _get(_base() + 'lastupdate.txt', timeout=10)
    if r.status_code != 200:
        raise IOError(f'http:{r.status_code}')
    for ln in r.text.splitlines():
        parts = ln.split()
        if parts and parts[-1].endswith('.export.CSV.zip'):
            return parts[-1].rsplit('/', 1)[-1].split('.')[0]
    raise IOError('bad_payload:gdelt_lastupdate')


def _fetch_batch(stamp):
    r = _get(_base() + f'{stamp}.export.CSV.zip')
    if r.status_code == 404:
        return []                      # lote que GDELT no publicó (pasa): cuenta como vacío
    if r.status_code != 200:
        raise IOError(f'http:{r.status_code}')
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        name = z.namelist()[0]
        text = z.read(name).decode('utf-8', 'replace')
    return parse_export(text, _ts_of(stamp).timestamp())


def refresh(now=None, max_new=MAX_PER_REFRESH):
    """Descarga los lotes nuevos (los más recientes primero). Devuelve error o None."""
    now = now or time.time()
    with _LOCK:
        if now - _STORE['checked'] < 120 and _STORE['batches']:
            return None                # otro hilo (otra capa) acaba de refrescar
        try:
            latest = _latest()
        except Exception as e:  # noqa: BLE001
            _STORE['errors'] += 1
            return str(e) if str(e).startswith(('http:', 'bad_payload:')) else f'conn:data.gdeltproject.org'
        _STORE['latest'], _STORE['checked'] = latest, now
        t = _ts_of(latest)
        cut = now - KEEP_S
        todo = []
        if not _STORE['batches']:
            max_new = min(max_new, 4)      # primer arranque: responde rápido con la última hora; el resto, después
        while t and t.timestamp() >= cut and len(todo) < max_new:
            st = t.strftime('%Y%m%d%H%M%S')
            if st not in _STORE['batches']:
                todo.append(st)
            t -= STEP
        err = None
        for st in todo:
            try:
                _STORE['batches'][st] = _fetch_batch(st)
            except Exception as e:  # noqa: BLE001
                err = str(e)[:120]
                log.info('gdelt_events: lote %s falló: %s', st, e)
                break
        for st in [k for k in _STORE['batches'] if (_ts_of(k) or datetime.now(timezone.utc)).timestamp() < cut]:
            _STORE['batches'].pop(st, None)
        return err if not _STORE['batches'] else None


def coverage(window_s, now=None):
    """(horas cargadas dentro de la ventana, horas de la ventana)."""
    now = now or time.time()
    n = sum(1 for k in _STORE['batches'] if (_ts_of(k).timestamp() >= now - window_s))
    return round(n * 0.25, 1), round(window_s / 3600, 1)


def aggregate(layer, window_s, severity_fn, now=None, limit=200):
    """Eventos de la capa en la ventana → puntos agrupados por lugar (~0,1°)."""
    now = now or time.time()
    groups = {}
    for k, evs in list(_STORE['batches'].items()):
        ts = _ts_of(k)
        if not ts or ts.timestamp() < now - window_s:
            continue
        for e in evs:
            if e[0] != layer:
                continue
            key = (round(e[1], 1), round(e[2], 1))
            g = groups.get(key)
            if g is None:
                g = groups[key] = {'lat': e[1], 'lon': e[2], 'place': e[3], 'cc': e[4], 'geo_type': e[5], 'articles': 0,
                                   'events': 0, 'sources': 0, 'urls': [], 'last': 0, 'codes': {}, 'gold': []}
            g['articles'] += e[6]
            g['sources'] += e[7]
            g['events'] += 1
            g['last'] = max(g['last'], e[9])
            g['codes'][e[10]] = g['codes'].get(e[10], 0) + 1
            if e[11] is not None:
                g['gold'].append(e[11])
            if e[8] and e[8] not in g['urls'] and len(g['urls']) < 3:
                g['urls'].append(e[8])
    return sorted(groups.values(), key=lambda g: -g['articles'])[:limit]


_CODE_LABEL = {
    '14': ('Protestas', 'Protests'), '141': ('Manifestación', 'Demonstration'), '143': ('Huelga/boicot', 'Strike/boycott'),
    '145': ('Protesta violenta', 'Violent protest'), '18': ('Asalto', 'Assault'), '180': ('Asalto', 'Assault'),
    '181': ('Secuestro', 'Abduction'), '183': ('Atentado/bomba', 'Bombing/attack'), '186': ('Asesinato', 'Assassination'),
    '19': ('Combates', 'Fighting'), '190': ('Combates', 'Fighting'), '193': ('Combate con armas pequeñas', 'Small-arms fighting'),
    '194': ('Combate con artillería/tanques', 'Artillery/tank fighting'), '195': ('Ataque aéreo', 'Aerial attack'),
    '20': ('Violencia masiva', 'Mass violence'), '15': ('Despliegue militar', 'Military posture'),
    '163': ('Embargo / sanciones', 'Embargo / sanctions'),
}


def label_of(code, lang_es=True):
    for k in (code, code[:3], code[:2]):
        if k in _CODE_LABEL:
            return _CODE_LABEL[k][0 if lang_es else 1]
    return None
