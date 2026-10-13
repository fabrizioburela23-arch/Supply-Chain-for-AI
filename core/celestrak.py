"""core/celestrak.py — satélites reales (CelesTrak) para el Space Monitor y el texto de Khipu.

Reporte de Fabrizio (2026-10-13): «¿por qué la del espacio ya no tiene los satélites?».
El código del globo dibuja todo lo que recibe; lo que fallaba era TRAERLO:

- /api/space/tle pedía los 11 grupos de CelesTrak UNO TRAS OTRO con 12 s de espera
  cada uno y sin parar ante un error. Con CelesTrak bloqueando o colgando la IP del
  servidor (su política: no más de una descarga por grupo cada ~2 h; quien insiste
  tras un 403 termina en su cortafuegos) la respuesta tardaba ~132 s: el globo se
  quedaba SIN satélites («Cargando satélites reales…») todo ese rato.
- Un resultado parcial o de respaldo no se guardaba (60 s de caché negativa), así
  que cada visita volvía a descargar los 11 grupos — y el texto de Khipu
  (`_space_constellations`) los descargaba OTRA vez por su cuenta. Eso es justo lo
  que hace que CelesTrak responda 403 y luego bloquee.

Ahora (un solo lugar para hablar con CelesTrak):
- Copia por grupo en memoria: un grupo descargado hace < 2 h NO se vuelve a pedir
  (CelesTrak publica cada ~2 h). La última copia buena se usa hasta 7 días y se
  marca `stale` con su hora (`as_of`): datos reales viejos, dichos como tales.
- Educado con la fuente: 403 «no ha cambiado» = la copia sigue vigente; 404 =
  grupo retirado (6 h sin pedirlo); cualquier otro fallo (403 de bloqueo, 429,
  5xx, red, tiempo agotado) PARA la ronda y pausa CelesTrak 30 min.
- Una ronda nunca pasa de DEADLINE_S (antes ~132 s).
- Sin ninguna copia → `fallback_tle()`: órbitas de REFERENCIA marcadas
  `source:'fallback'` (la UI lo dice: «ref», «no en vivo»), nunca como reales.
"""
import logging
import math
import threading
import time
from datetime import datetime, timezone

import requests

log = logging.getLogger('celestrak')

URL = 'https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle'
_UA = 'KhipuFinance/1.0 (+space-monitor)'

# Grupos de CelesTrak → (nombre visible, nodo Khipu vinculado, color hex)
GROUPS = [
    ('starlink',      'Starlink',        'SpaceX',           '#ff7a45'),
    ('oneweb',        'OneWeb',          'EutelsatOneWeb',   '#36cfc9'),
    ('planet',        'Planet Labs',     'PlanetLabs',       '#73d13d'),
    ('spire',         'Spire Global',    'Spire',            '#9254de'),
    ('iridium-NEXT',  'Iridium NEXT',    'Iridium',          '#40a9ff'),
    ('globalstar',    'Globalstar',      'Globalstar',       '#f759ab'),
    ('ses',           'SES / O3b',       'SES',              '#ffc53d'),
    ('gps-ops',       'GPS',             None,               '#bfbfbf'),
    ('galileo',       'Galileo',         None,               '#597ef7'),
    ('beidou',        'BeiDou',          None,               '#ff4d4f'),
    ('stations',      'Estaciones (ISS/CSS)', None,          '#ffffff'),
]
# Tope de satélites RENDERIZADOS por grupo (los conteos reportados son los reales).
RENDER_CAP = {'starlink': 1200, 'oneweb': 400, 'planet': 250, '_default': 220}

FRESH_S = 2 * 3600          # CelesTrak actualiza los GP cada ~2 h: antes no se vuelve a pedir
STALE_S = 6 * 3600          # una copia más vieja se muestra como «copia» con su hora
KEEP_S = 7 * 86400          # la última copia buena se usa hasta 7 días
GONE_BACKOFF_S = 6 * 3600   # 404 (grupo retirado/renombrado)
PAUSE_S = 1800              # bloqueo/límite/red: 30 min sin pedirle nada a CelesTrak
DEADLINE_S = 20.0           # una ronda completa nunca pasa de esto
TIMEOUT = (4, 8)            # (conectar, leer) por grupo

_LOCK = threading.Lock()        # protege _STORE/_ERR/_PAUSE
_FETCH = threading.Lock()       # UNA ronda de descarga a la vez
_STORE = {}                     # group → {'sats': [{name,l1,l2}], 'fetched': ts}
_ERR = {}                       # group → {'error': str, 'retry_at': ts}
_PAUSE = {'until': 0.0, 'why': ''}


def _now():
    return time.time()


def _iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def reset():
    """Solo tests."""
    with _LOCK:
        _STORE.clear(); _ERR.clear(); _PAUSE.update(until=0.0, why='')


def parse_tle_text(txt):
    """Parsea formato TLE de 3 líneas → [{name,l1,l2}]."""
    out = []
    lines = [ln.rstrip() for ln in (txt or '').splitlines() if ln.strip()]
    i = 0
    while i + 2 < len(lines):
        name, l1, l2 = lines[i], lines[i + 1], lines[i + 2]
        if l1.startswith('1 ') and l2.startswith('2 '):
            out.append({'name': name.strip(), 'l1': l1, 'l2': l2})
            i += 3
        else:
            i += 1
    return out


def _not_updated(r):
    """403 de CelesTrak «GP data has not updated since your last successful download»:
    NO es un fallo — nuestra copia sigue siendo la vigente."""
    try:
        return r.status_code == 403 and 'not updated' in (r.text or '')[:300].lower()
    except Exception:  # noqa: BLE001
        return False


def refresh(now=None):
    """Una ronda educada de descarga (solo los grupos que lo necesitan). Nunca lanza."""
    if not _FETCH.acquire(timeout=DEADLINE_S + 5):
        return                                     # otra ronda en curso: se sirve lo guardado
    try:
        start = time.monotonic()
        for group, label, _node, _color in GROUPS:
            now_ = _now() if now is None else now
            with _LOCK:
                if _PAUSE['until'] > now_:
                    return
                have = _STORE.get(group)
                if have and now_ - have['fetched'] < FRESH_S:
                    continue
                err = _ERR.get(group)
                if err and err['retry_at'] > now_:
                    continue
            if time.monotonic() - start > DEADLINE_S:
                with _LOCK:
                    _ERR[group] = {'error': 'sin tiempo en esta ronda', 'retry_at': now_ + 60}
                continue
            try:
                r = requests.get(URL.format(group=group), timeout=TIMEOUT, headers={'User-Agent': _UA})
            except Exception as e:  # noqa: BLE001  red, DNS, tiempo agotado (cortafuegos que descarta)
                _pause(now_, f'{type(e).__name__}: {str(e)[:60]}')
                return
            code = getattr(r, 'status_code', 0)
            if getattr(r, 'ok', False) and r.text and r.text.lstrip()[:1] != '<':
                parsed = parse_tle_text(r.text)
                if parsed:
                    with _LOCK:
                        _STORE[group] = {'sats': parsed, 'fetched': now_}
                        _ERR.pop(group, None)
                    continue
                with _LOCK:
                    _ERR[group] = {'error': 'sin TLEs', 'retry_at': now_ + GONE_BACKOFF_S}
                continue
            if _not_updated(r):
                with _LOCK:
                    if group in _STORE:
                        _STORE[group]['fetched'] = now_    # la copia sigue vigente
                        _ERR.pop(group, None)
                    else:
                        _ERR[group] = {'error': 'HTTP 403 (sin cambios desde la última descarga)',
                                       'retry_at': now_ + FRESH_S}
                continue
            if code == 404:
                with _LOCK:
                    _ERR[group] = {'error': 'HTTP 404', 'retry_at': now_ + GONE_BACKOFF_S}
                continue
            # 403 de bloqueo, 429, 5xx…: la política de CelesTrak pide PARAR ante un no-200
            _pause(now_, f'HTTP {code}' + (' (HTML)' if code == 200 else ''))
            return
    finally:
        _FETCH.release()


def _pause(now_, why):
    with _LOCK:
        _PAUSE.update(until=now_ + PAUSE_S, why=why)
    log.warning('CelesTrak en pausa %d s: %s', PAUSE_S, why)


def _usable(now_):
    """[(idx, group, label, node, color, entry|None, err|None)] con copias ≤ KEEP_S."""
    out = []
    with _LOCK:
        pause = dict(_PAUSE)
        for idx, (group, label, node, color) in enumerate(GROUPS):
            e = _STORE.get(group)
            if e and now_ - e['fetched'] > KEEP_S:
                e = None
            err = (_ERR.get(group) or {}).get('error')
            if not err and pause['until'] > now_ and not (e and now_ - e['fetched'] < FRESH_S):
                err = 'CelesTrak en pausa: ' + pause['why']
            out.append((idx, group, label, node, color, e, err))
    return out, pause


def payload(now=None):
    """Respuesta de /api/space/tle: {constellations, sats, total_real, rendered, source, …}."""
    refresh(now)
    now_ = _now() if now is None else now
    rows, pause = _usable(now_)
    constellations, sats = [], []
    any_ok = False
    for idx, group, label, node, color, e, err in rows:
        if not e:
            constellations.append({'name': label, 'count': 0, 'rendered': 0, 'node': node, 'color': color,
                                   'error': (err or 'sin datos')[:80]})
            continue
        any_ok = True
        parsed = e['sats']
        real = len(parsed)
        cap = RENDER_CAP.get(group, RENDER_CAP['_default'])
        sampled = [parsed[int(k * real / cap)] for k in range(cap)] if real > cap else parsed
        sats.extend({'n': s['name'], 'l1': s['l1'], 'l2': s['l2'], 'c': idx} for s in sampled)
        age = now_ - e['fetched']
        c = {'name': label, 'count': real, 'rendered': len(sampled), 'node': node, 'color': color,
             'as_of': _iso(e['fetched'])}
        if age > STALE_S:
            c['stale'] = True
        constellations.append(c)
    if not any_ok:
        out = fallback_tle()
        out['reason'] = pause['why'] or next((r[6] for r in rows if r[6]), '') or 'sin datos'
        if pause['until'] > now_:
            out['retry_after'] = _iso(pause['until'])
        return out
    return {'constellations': constellations, 'sats': sats,
            'total_real': sum(c['count'] for c in constellations), 'rendered': len(sats),
            'source': 'celestrak', 'stale': any(c.get('stale') or c.get('error') for c in constellations),
            'as_of': max(c['as_of'] for c in constellations if c.get('as_of'))}


def counts(now=None):
    """{label: count} de los grupos con copia REAL (para el texto de Khipu). Sin descarga extra."""
    refresh(now)
    rows, _pause_ = _usable(_now() if now is None else now)
    return {label: len(e['sats']) for _i, _g, label, _n, _c, e, _err in rows if e}


def fallback_tle():
    """Órbitas de REFERENCIA cuando CelesTrak no es alcanzable (source='fallback'; la UI dice «ref»)."""
    groups = [('Starlink', 'SpaceX', '#ff7a45', 7134, 550, 53.0),
              ('OneWeb', 'EutelsatOneWeb', '#36cfc9', 648, 1200, 87.9),
              ('Planet Labs', 'PlanetLabs', '#73d13d', 200, 475, 97.4),
              ('Iridium NEXT', 'Iridium', '#40a9ff', 75, 780, 86.4),
              ('GPS', None, '#bfbfbf', 31, 20180, 55.0)]
    constellations, sats = [], []
    for idx, (label, node, color, real, alt_km, inc) in enumerate(groups):
        rendered = min(real, 200 if label == 'Starlink' else 80)
        constellations.append({'name': label, 'count': real, 'rendered': rendered,
                               'node': node, 'color': color})
        # genera líneas TLE plausibles distribuyendo RAAN/anomalía
        for k in range(rendered):
            raan = (360.0 * k / rendered) % 360
            ma = (137.5 * k) % 360
            mm = 86400.0 / (2 * math.pi * math.sqrt(((6371 + alt_km) * 1000) ** 3 / 3.986e14))
            l1 = f'1 {10000 + idx * 1000 + k:05d}U 24001A   24001.00000000  .00000000  00000-0  00000-0 0  9990'
            l2 = (f'2 {10000 + idx * 1000 + k:05d} {inc:8.4f} {raan:8.4f} 0001000 '
                  f'  0.0000 {ma:8.4f} {mm:11.8f}00000')
            sats.append({'n': f'{label}-{k}', 'l1': l1, 'l2': l2, 'c': idx})
    return {'constellations': constellations, 'sats': sats,
            'total_real': sum(c['count'] for c in constellations),
            'rendered': len(sats), 'source': 'fallback'}
