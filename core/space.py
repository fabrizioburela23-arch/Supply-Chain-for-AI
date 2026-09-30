"""core/space.py — SPACE MONITOR (pestaña 🚀 Espacio): /api/space2/*.

Pedido de Fabrizio (2026-09-30): "lo mismo que el World Monitor, para Espacio;
los lanzamientos DINÁMICOS, no una lista". La vista (engine/spacemonitor.js)
dibuja plataformas de lanzamiento brillando en el globo, arcos de ascenso desde
las coordenadas REALES de cada plataforma, una cuenta regresiva en vivo y una
línea de tiempo de lanzamientos. Este módulo es su backend.

Fuente: Launch Library 2 (The Space Devs) — https://ll.thespacedevs.com.
- Plan gratuito = 15 consultas/hora por IP. Por eso: caché ≥ 10 min por
  ventana (upcoming 15 min, previous 30 min), UNA consulta a la vez por ventana,
  presupuesto propio de ≤ 12 consultas/hora (margen para /api/space/launches, que
  sigue existiendo en server.py) y, si la fuente falla o nos limita, se sirven
  los datos anteriores marcados `stale` con su hora. Nunca se inventa: sin datos
  la respuesta dice por qué (error_code + error_es/error_en, como core/world.py).
- Coordenadas: SOLO pad.latitude/pad.longitude de la API. Si faltan o no son
  válidas, `pad.lat/lon` quedan en None y el cliente NO lo dibuja en el globo.
- Empresas del grafo: proveedor del lanzamiento, agencias/clientes de la misión
  y fabricante del cohete se resuelven con core.entities.resolve (umbral de
  BÚSQUEDA, 60) + una tabla CURADA y corta de palabras clave de misión
  (p.ej. "Kuiper" → Amazon) que se etiqueta como tal (method='mission_keyword').

La base de LL2 es configurable sin tocar código (lección sept-2026: los
proveedores retiran versiones): SPACE_LL2_BASE (default .../2.2.0).

Endpoints:
  GET /api/space2/launches?window=upcoming|previous&limit=1..100
  GET /api/space2/summary
"""
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone

import requests
from flask import Blueprint, jsonify, request

from core.http import rate_limit

log = logging.getLogger('space')

space_bp = Blueprint('space2', __name__, url_prefix='/api/space2')

PROVIDER = 'Launch Library 2 (The Space Devs)'
_UA = 'KhipuFinance/1.0 (+space-monitor)'
WINDOWS = ('upcoming', 'previous')
FETCH_LIMIT = {'upcoming': 60, 'previous': 40}      # por consulta a LL2 (máx. 100)
TTL = {'upcoming': 900, 'previous': 1800}           # ≥ 10 min (plan gratuito)
ERROR_TTL = 300              # tras un fallo no se reintenta antes de 5 min
RATE_LIMIT_TTL = 1200        # si LL2 responde 429, 20 min de silencio
HOURLY_BUDGET = 12           # consultas/hora propias (LL2 permite 15)
HTTP_TIMEOUT = 9

# id de estado de LL2 → tipo normalizado
_STATUS_KIND = {1: 'go', 2: 'tbd', 3: 'success', 4: 'failure', 5: 'hold', 6: 'inflight',
                7: 'partial', 8: 'tbc'}
_ABBREV_KIND = {'go': 'go', 'tbd': 'tbd', 'success': 'success', 'failure': 'failure',
                'hold': 'hold', 'in flight': 'inflight', 'partial failure': 'partial', 'tbc': 'tbc'}
FINAL_KINDS = ('success', 'failure', 'partial')

# Palabras clave CURADAS de misión → nodo del grafo (dueño de la carga). Solo
# constelaciones/misiones inequívocas; el cliente lo muestra como "por nombre
# de misión". Si el nodo no existe en el snapshot, se ignora.
MISSION_KEYWORDS = [
    (re.compile(r'\bstarlink\b', re.I), 'SpaceX'),
    (re.compile(r'\bkuiper\b', re.I), 'Amazon'),
    (re.compile(r'\boneweb\b', re.I), 'Eutelsat'),
    (re.compile(r'\bblue ?birds?\b', re.I), 'AST_SpaceMobile'),
    (re.compile(r'\b(flock|pelican|skysat|tanager)\b', re.I), 'PlanetLabs'),
    (re.compile(r'\blemur\b', re.I), 'SpireGlobal'),
    (re.compile(r'\biridium\b', re.I), 'Iridium'),
    (re.compile(r'\bglobalstar\b', re.I), 'Globalstar'),
    (re.compile(r'\bo3b\b|\bses[- ]\d', re.I), 'SES'),
    (re.compile(r'\bviasat\b', re.I), 'Viasat'),
    (re.compile(r'\bblacksky\b|\bgen-?3\b', re.I), 'BlackSky'),
    (re.compile(r'\bworldview legion\b', re.I), 'Maxar'),
    (re.compile(r'\biceye\b', re.I), 'ICEYE'),
    (re.compile(r'\bcapella\b|\bacadia\b', re.I), 'CapellaSpace'),
    (re.compile(r'\bumbra\b', re.I), 'Umbra'),
    (re.compile(r'\bhawkeye ?360\b|\bcluster \d', re.I), 'HawkEye360'),
    (re.compile(r'\bnusat\b|\bsatellogic\b', re.I), 'Satellogic'),
    (re.compile(r'\bim-\d\b|\bnova-c\b', re.I), 'IntuitiveMachines'),
    (re.compile(r'\bcygnus\b|\bng-\d{2}\b', re.I), 'Northrop'),
    (re.compile(r'\bstarliner\b', re.I), 'Boeing'),
]
# Palabras genéricas que se quitan al final de un nombre de agencia para un 2º
# intento de resolución ("Northrop Grumman Space Systems" → "Northrop Grumman").
_GENERIC_TAIL = re.compile(r'(\s+(space|systems?|aerospace|launch|services|corporation|corp|company|'
                           r'industries|technologies|technology|inc|llc|ltd|gmbh|s\.?a\.?))+\s*$', re.I)
_PAREN = re.compile(r'\(([^)]{2,40})\)')
_URL_OK = re.compile(r'^https?://', re.I)
ROLE_ORDER = {'provider': 0, 'customer': 1, 'payload': 2, 'manufacturer': 3}


def _now():
    return time.time()


def _iso(ts):
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace('Z', '+00:00')).timestamp()
    except (TypeError, ValueError):
        return None


def _safe_url(u):
    """Solo http(s): un feed alterado no puede colar javascript:/data:."""
    if not isinstance(u, str):
        return None
    u = u.strip()
    return u if _URL_OK.match(u) else None


def _float(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None      # NaN → None


def _valid_ll(lat, lon):
    return lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180 \
        and not (lat == 0 and lon == 0)


def _txt(v, n=300):
    if v is None:
        return None
    s = re.sub(r'\s+', ' ', str(v)).strip()
    return s[:n] if s else None


def err_info(err):
    """Código de error → {error_code, error_es, error_en, error} (bilingüe)."""
    try:
        from core.world import err_info as _wi
        out = _wi(err)
    except Exception:  # noqa: BLE001
        out = {'error_code': 'other', 'error_es': str(err), 'error_en': str(err), 'error': str(err)}
    e = str(err or '')
    if e == 'budget':
        out = {'error_code': 'budget',
               'error_es': 'pausa para respetar el límite gratuito de Launch Library 2 (15/hora)',
               'error_en': 'paused to respect the Launch Library 2 free limit (15/hour)'}
        out['error'] = out['error_en']
    elif e == 'backoff':
        out = {'error_code': 'backoff',
               'error_es': 'la última consulta falló: reintento en unos minutos',
               'error_en': 'the last fetch failed: retrying in a few minutes'}
        out['error'] = out['error_en']
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 1. Grafo (nodos + NRS réplica del cliente) — reutiliza core/world.py
# ═══════════════════════════════════════════════════════════════════════════
def _graph_by_id():
    try:
        from core.world import _graph
        return _graph().get('by_id') or {}
    except Exception as e:  # noqa: BLE001
        log.warning('space: grafo no disponible: %s', e)
        return {}


def _resolve(text):
    """core.entities.resolve con umbral de BÚSQUEDA. None si no llega."""
    if not text:
        return None
    try:
        from core.entities import resolve, UMBRAL_BUSQUEDA
    except Exception:  # noqa: BLE001
        return None
    try:
        return resolve(text, umbral=UMBRAL_BUSQUEDA)
    except Exception:  # noqa: BLE001
        return None


def resolve_org(name, abbrev=None):
    """Resuelve un nombre de organización de LL2 al grafo. Intenta: nombre
    completo · abreviatura (solo coincidencia exacta de id/label/alias: una
    sigla que choca con un ticker NO cuenta) · sigla entre paréntesis
    ('… (ROSCOSMOS)') y el nombre sin ella · nombre sin cola genérica
    ('Space Systems', 'Aerospace'…). Un paréntesis que NO es sigla es un
    calificativo ('iSpace (China)' ≠ ispace de Japón): entonces no se recorta.
    Devuelve el hit de resolve() o None."""
    tries = []
    if name:
        tries.append((name, None))
    if abbrev and abbrev != name and len(str(abbrev)) >= 3:
        tries.append((abbrev, ('id', 'label', 'alias')))
    if name:
        m = _PAREN.search(name)
        acr = bool(m and re.fullmatch(r'[A-Z0-9][A-Z0-9 .&-]{2,}', m.group(1).strip()))
        if m and acr:
            tries.append((m.group(1).strip(), ('id', 'label', 'alias')))
            tries.append((_PAREN.sub('', name).strip(), None))
        if not m or acr:
            tail = _GENERIC_TAIL.sub('', _PAREN.sub('', name)).strip()
            if tail and tail != name and len(tail) >= 4:
                tries.append((tail, None))
    seen = set()
    for t, methods in tries:
        k = str(t).strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        r = _resolve(t)
        if r and (methods is None or r.get('method') in methods):
            return r
    return None


def match_graph(provider, agencies, mission_name, launch_name, manufacturer=None):
    """Empresas del grafo implicadas en un lanzamiento.
    provider/manufacturer: {'name','abbrev'} · agencies: [{'name','abbrev'}]."""
    by_id = _graph_by_id()
    out = {}

    def add(hit, role, method=None, matched=None):
        if not hit:
            return
        nid = hit['id'] if isinstance(hit, dict) else hit
        rec = by_id.get(nid)
        if by_id and not rec:
            return
        cur = out.get(nid)
        if cur and ROLE_ORDER.get(cur['role'], 9) <= ROLE_ORDER.get(role, 9):
            return
        rec = rec or {}
        out[nid] = {
            'id': nid, 'label': rec.get('label') or (hit.get('label') if isinstance(hit, dict) else nid),
            'role': role, 'ticker': rec.get('ticker') or None, 'nrs': rec.get('nrs'),
            'sector': rec.get('sector'),
            'method': method or (hit.get('method') if isinstance(hit, dict) else 'curated'),
            'score': hit.get('score') if isinstance(hit, dict) else None,
            'matched': matched or (hit.get('matched') if isinstance(hit, dict) else None),
        }

    if provider and provider.get('name'):
        add(resolve_org(provider.get('name'), provider.get('abbrev')), 'provider')
    for ag in agencies or []:
        if ag and ag.get('name'):
            add(resolve_org(ag.get('name'), ag.get('abbrev')), 'customer')
    text = ' '.join(x for x in (mission_name, launch_name) if x)
    for rx, nid in MISSION_KEYWORDS:
        m = rx.search(text)
        if m:
            add({'id': nid, 'label': nid, 'score': None, 'method': 'mission_keyword',
                 'matched': m.group(0)}, 'payload', 'mission_keyword', m.group(0))
    if manufacturer and manufacturer.get('name'):
        add(resolve_org(manufacturer.get('name'), manufacturer.get('abbrev')), 'manufacturer')
    return sorted(out.values(), key=lambda r: (ROLE_ORDER.get(r['role'], 9), r['label']))


# ═══════════════════════════════════════════════════════════════════════════
# 2. Normalización de un lanzamiento de LL2 (2.2.0 normal/detailed y 2.3.0)
# ═══════════════════════════════════════════════════════════════════════════
def _status(st):
    st = st or {}
    sid = st.get('id')
    kind = _STATUS_KIND.get(sid) if isinstance(sid, int) else None
    if not kind:
        kind = _ABBREV_KIND.get(str(st.get('abbrev') or st.get('name') or '').strip().lower(), 'other')
    return {'id': sid, 'abbrev': _txt(st.get('abbrev'), 20), 'name': _txt(st.get('name'), 60),
            'description': _txt(st.get('description'), 240), 'kind': kind}


def _org(o):
    if not isinstance(o, dict) or not o.get('name'):
        return None
    return {'name': _txt(o.get('name'), 120), 'abbrev': _txt(o.get('abbrev'), 24),
            'type': _txt(o.get('type') if not isinstance(o.get('type'), dict) else o['type'].get('name'), 40),
            'country_code': _txt(o.get('country_code'), 40)}


def _vids(raw):
    out = []
    for v in raw.get('vidURLs') or raw.get('vid_urls') or []:
        if isinstance(v, str):
            u = _safe_url(v)
            if u:
                out.append({'url': u, 'title': None, 'source': None})
            continue
        if not isinstance(v, dict):
            continue
        u = _safe_url(v.get('url'))
        if not u:
            continue
        out.append({'url': u, 'title': _txt(v.get('title'), 140), 'source': _txt(v.get('source') or v.get('publisher'), 60),
                    'priority': v.get('priority'), 'live': v.get('live')})
    out.sort(key=lambda x: (x.get('priority') if isinstance(x.get('priority'), int) else 99))
    return out[:4]


def _infos(raw):
    out = []
    for v in raw.get('infoURLs') or raw.get('info_urls') or []:
        u = _safe_url(v if isinstance(v, str) else (v or {}).get('url'))
        if u:
            out.append({'url': u, 'title': None if isinstance(v, str) else _txt(v.get('title'), 140)})
    return out[:3]


def normalize_launch(raw, match=True):
    """Lanzamiento LL2 → forma estable del Space Monitor. None si no es válido."""
    if not isinstance(raw, dict) or not raw.get('id'):
        return None
    net_ts = _parse_iso(raw.get('net'))
    ws, we = _parse_iso(raw.get('window_start')), _parse_iso(raw.get('window_end'))
    lsp = _org(raw.get('launch_service_provider'))
    rk = raw.get('rocket') or {}
    cfg = rk.get('configuration') or {}
    manu = _org(cfg.get('manufacturer'))
    ms = raw.get('mission') or {}
    orbit = ms.get('orbit') or {}
    agencies = [a for a in (_org(x) for x in (ms.get('agencies') or [])) if a]
    pad = raw.get('pad') or {}
    loc = pad.get('location') or {}
    lat, lon = _float(pad.get('latitude')), _float(pad.get('longitude'))
    if not _valid_ll(lat, lon):
        lat = lon = None
    npcs = raw.get('net_precision')
    img = raw.get('image')
    if isinstance(img, dict):
        img = img.get('thumbnail_url') or img.get('image_url')
    rec = {
        'id': str(raw.get('id'))[:64],
        'name': _txt(raw.get('name'), 160),
        'net': _iso(net_ts) if net_ts else None, 'net_ts': net_ts,
        'net_precision': _txt(npcs.get('name') if isinstance(npcs, dict) else npcs, 40),
        'window_start': _iso(ws) if ws else None, 'window_end': _iso(we) if we else None,
        'status': _status(raw.get('status')),
        'probability': raw.get('probability') if isinstance(raw.get('probability'), (int, float)) else None,
        'holdreason': _txt(raw.get('holdreason'), 240), 'failreason': _txt(raw.get('failreason'), 300),
        'provider': lsp,
        'rocket': {'name': _txt(cfg.get('name'), 80), 'full_name': _txt(cfg.get('full_name'), 100),
                   'family': _txt(cfg.get('family'), 60), 'variant': _txt(cfg.get('variant'), 40),
                   'manufacturer': manu},
        'mission': {'name': _txt(ms.get('name'), 140), 'type': _txt(ms.get('type'), 60),
                    'description': _txt(ms.get('description'), 600),
                    'orbit': {'name': _txt(orbit.get('name'), 60), 'abbrev': _txt(orbit.get('abbrev'), 16)}
                    if orbit else None,
                    'agencies': agencies} if ms else None,
        'pad': {'name': _txt(pad.get('name'), 120), 'lat': lat, 'lon': lon,
                'location': _txt(loc.get('name'), 120),
                'country_code': _txt(loc.get('country_code') or pad.get('country_code'), 8),
                'map_url': _safe_url(pad.get('map_url')), 'wiki_url': _safe_url(pad.get('wiki_url'))}
        if pad else None,
        'webcast_live': bool(raw.get('webcast_live')),
        'vid_urls': _vids(raw) or _vids(ms),
        'info_urls': _infos(raw) or _infos(ms),
        'image': _safe_url(img),
        'url': _safe_url(raw.get('url')),
    }
    if match:
        rec['graph'] = match_graph(lsp, agencies, rec['mission']['name'] if rec['mission'] else None,
                                   rec['name'], manu)
    return rec


def normalize_payload(payload, match=True):
    """Respuesta LL2 ({results:[…]}) → lista normalizada. Lanza ValueError si
    el formato no es el esperado."""
    if not isinstance(payload, dict) or not isinstance(payload.get('results'), list):
        raise ValueError('bad_payload:ll2')
    out = []
    for raw in payload['results']:
        try:
            r = normalize_launch(raw, match=match)
        except Exception as e:  # noqa: BLE001 — un lanzamiento raro no tumba la lista
            log.debug('space: lanzamiento descartado: %s', e)
            r = None
        if r:
            out.append(r)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 3. Caché + presupuesto de consultas (stale-on-error)
# ═══════════════════════════════════════════════════════════════════════════
_LOCK = threading.Lock()
_FETCH_LOCKS = {w: threading.Lock() for w in WINDOWS}
_CACHE = {}              # window → {'data','fetched','err','err_ts','retry_at'}
_CALLS = []              # timestamps de consultas a LL2 (última hora)


def _reset_cache():
    with _LOCK:
        _CACHE.clear()
        del _CALLS[:]


def ll2_base():
    return (os.environ.get('SPACE_LL2_BASE') or 'https://ll.thespacedevs.com/2.2.0').rstrip('/')


def _budget_ok(now):
    with _LOCK:
        _CALLS[:] = [t for t in _CALLS if now - t < 3600]
        if len(_CALLS) >= HOURLY_BUDGET:
            return False
        _CALLS.append(now)
        return True


def _http_get_json(url, params=None, timeout=HTTP_TIMEOUT):
    try:
        r = requests.get(url, params=params, timeout=timeout,
                         headers={'User-Agent': _UA, 'Accept': 'application/json'})
    except requests.exceptions.Timeout:
        return None, 'timeout'
    except requests.exceptions.ConnectionError:
        host = re.sub(r'^https?://([^/]+).*$', r'\1', url)
        return None, f'conn:{host}'
    except Exception as e:  # noqa: BLE001
        return None, f'exc:{type(e).__name__}: {str(e)[:100]}'
    if r.status_code == 429:
        return None, 'rate_limited'
    if r.status_code != 200:
        return None, f'http:{r.status_code}'
    try:
        return r.json(), None
    except ValueError:
        return None, 'nonjson:' + (r.text or '')[:80].strip()


def _fetch(window):
    """Una consulta a LL2 → (lista_normalizada, código_error)."""
    params = {'limit': FETCH_LIMIT[window], 'mode': 'detailed', 'format': 'json'}
    if window == 'upcoming':
        params['hide_recent_previous'] = 'true'
    data, err = _http_get_json(f'{ll2_base()}/launch/{window}/', params=params)
    if err:
        return None, err
    try:
        return normalize_payload(data), None
    except ValueError as e:
        return None, str(e)


def get_launches(window):
    """Lanzamientos de la ventana (caché) + estado honesto de la fuente."""
    now = _now()
    with _LOCK:
        e = dict(_CACHE.get(window) or {})
    fresh = e.get('data') is not None and e.get('fetched') and now - e['fetched'] < TTL[window]
    err = None
    if not fresh:
        if e.get('retry_at') and now < e['retry_at']:
            err = e.get('err') or 'backoff'
        elif not _FETCH_LOCKS[window].acquire(blocking=False):
            err = 'refreshing' if e.get('data') is not None else 'pending'
        else:
            try:
                if not _budget_ok(now):
                    err = 'budget'
                else:
                    data, err = _fetch(window)
                    with _LOCK:
                        cur = _CACHE.setdefault(window, {})
                        if err:
                            cur['err'], cur['err_ts'] = err, now
                            cur['retry_at'] = now + (RATE_LIMIT_TTL if err == 'rate_limited' else ERROR_TTL)
                        else:
                            cur.update({'data': data, 'fetched': now, 'err': None, 'err_ts': None,
                                        'retry_at': None})
                    if err:
                        log.warning('space: LL2 %s falló: %s', window, err)
            finally:
                _FETCH_LOCKS[window].release()
        with _LOCK:
            e = dict(_CACHE.get(window) or {})
    data = e.get('data')
    ok = data is not None and not err
    src = {'provider': PROVIDER, 'feed': f'{ll2_base()}/launch/{window}/', 'ok': ok,
           'stale': bool(err and data is not None), 'as_of': _iso(e.get('fetched')) if e.get('fetched') else None,
           'count': len(data or []), 'ttl_s': TTL[window]}
    if err:
        src.update(err_info(err))
        if err in ('pending', 'refreshing'):
            src['pending'] = err == 'pending'
    return list(data or []), src


# ═══════════════════════════════════════════════════════════════════════════
# 4. Resumen ("Situación espacial")
# ═══════════════════════════════════════════════════════════════════════════
def _provider_name(l):
    p = l.get('provider') or {}
    return p.get('name') or '?'


def _count_by_provider(items):
    agg = {}
    for l in items:
        name = _provider_name(l)
        a = agg.setdefault(name, {'name': name, 'abbrev': (l.get('provider') or {}).get('abbrev'),
                                  'count': 0, 'graph_id': None})
        a['count'] += 1
        if not a['graph_id']:
            for g in l.get('graph') or []:
                if g.get('role') == 'provider':
                    a['graph_id'] = g['id']
                    break
    return sorted(agg.values(), key=lambda a: (-a['count'], a['name']))


def next_launch(upcoming, now=None):
    now = now or _now()
    for l in sorted((x for x in upcoming if x.get('net_ts')), key=lambda x: x['net_ts']):
        if l['status']['kind'] in FINAL_KINDS:
            continue
        # in flight o pendiente dentro de la última hora sigue siendo "el próximo"
        if l['net_ts'] >= now - 3600 or l['status']['kind'] == 'inflight':
            return l
    return None


def summarize(upcoming, previous, now=None):
    now = now or _now()
    up = [l for l in upcoming if l.get('net_ts')]
    prev = [l for l in previous if l.get('net_ts')]
    up_last = max((l['net_ts'] for l in up), default=None)
    prev_first = min((l['net_ts'] for l in prev), default=None)

    def span(days, past=False):
        lim = now - days * 86400 if past else now + days * 86400
        if past:
            items = [l for l in prev if lim <= l['net_ts'] <= now]
            truncated = bool(prev_first and prev_first > lim and len(prev) >= FETCH_LIMIT['previous'])
        else:
            items = [l for l in up if now - 3600 <= l['net_ts'] <= lim]
            truncated = bool(up_last and up_last < lim and len(up) >= FETCH_LIMIT['upcoming'])
        return items, truncated

    wk, wk_tr = span(7)
    mo, mo_tr = span(30)
    pwk, pwk_tr = span(7, past=True)
    pmo, pmo_tr = span(30, past=True)
    outcome = {'success': 0, 'failure': 0, 'partial': 0, 'other': 0}
    for l in pmo:
        k = l['status']['kind']
        outcome[k if k in outcome else 'other'] += 1

    pads = {}
    for l in up:
        p = l.get('pad') or {}
        if p.get('lat') is None:
            continue
        key = f"{p.get('name')}|{p['lat']:.3f}|{p['lon']:.3f}"
        a = pads.setdefault(key, {'key': key, 'name': p.get('name'), 'location': p.get('location'),
                                  'country_code': p.get('country_code'), 'lat': p['lat'], 'lon': p['lon'],
                                  'upcoming': 0, 'next_net': None, 'launch_ids': []})
        a['upcoming'] += 1
        a['launch_ids'].append(l['id'])
        if l['net_ts'] >= now - 3600 and (a['next_net'] is None or l['net'] < a['next_net']):
            a['next_net'] = l['net']

    comp = {}
    for scope, items in (('upcoming', up), ('recent', pmo)):
        for l in items:
            for g in l.get('graph') or []:
                c = comp.setdefault(g['id'], {'id': g['id'], 'label': g['label'], 'ticker': g.get('ticker'),
                                              'nrs': g.get('nrs'), 'upcoming': 0, 'recent': 0, 'roles': []})
                c[scope] += 1
                if g['role'] not in c['roles']:
                    c['roles'].append(g['role'])
    companies = sorted(comp.values(), key=lambda c: (-(c['upcoming'] + c['recent']), c['label']))
    with_graph = sum(1 for l in up if l.get('graph'))
    nl = next_launch(up, now)
    return {
        'as_of': _iso(now),
        'next': nl,
        'counts': {'upcoming_7d': len(wk), 'upcoming_30d': len(mo), 'upcoming_7d_truncated': wk_tr,
                   'upcoming_30d_truncated': mo_tr, 'previous_7d': len(pwk), 'previous_30d': len(pmo),
                   'previous_7d_truncated': pwk_tr, 'previous_30d_truncated': pmo_tr,
                   'upcoming_loaded': len(up), 'previous_loaded': len(prev),
                   'upcoming_horizon': _iso(up_last) if up_last else None,
                   'previous_horizon': _iso(prev_first) if prev_first else None},
        'by_provider': {'week': _count_by_provider(wk), 'month': _count_by_provider(mo),
                        'past_month': _count_by_provider(pmo)},
        'outcomes_30d': outcome,
        'pads': sorted(pads.values(), key=lambda a: (-a['upcoming'], a['name'] or '')),
        'graph': {'companies': companies[:40], 'launches_with_graph': with_graph,
                  'upcoming_total': len(up)},
    }


# ═══════════════════════════════════════════════════════════════════════════
# 5. Endpoints
# ═══════════════════════════════════════════════════════════════════════════
def _bad(code, es, en, status=400):
    return jsonify({'error': en, 'error_code': code, 'error_es': es, 'error_en': en}), status


@space_bp.get('/launches')
@rate_limit(300, 3600)
def api_space2_launches():
    """GET /api/space2/launches?window=upcoming|previous&limit=30"""
    window = request.args.get('window', 'upcoming')
    if window not in WINDOWS:
        return _bad('bad_window', 'window debe ser upcoming o previous', 'window must be upcoming or previous')
    try:
        limit = int(request.args.get('limit', 30))
    except (TypeError, ValueError):
        return _bad('bad_limit', 'limit inválido (1-100)', 'invalid limit (1-100)')
    if not 1 <= limit <= 100:
        return _bad('bad_limit', 'limit inválido (1-100)', 'invalid limit (1-100)')
    data, src = get_launches(window)
    if window == 'upcoming':
        data = sorted(data, key=lambda l: (l.get('net_ts') is None, l.get('net_ts') or 0))
    else:
        data = sorted(data, key=lambda l: -(l.get('net_ts') or 0))
    return jsonify({'window': window, 'as_of': _iso(_now()), 'source': src,
                    'count': min(limit, len(data)), 'launches': data[:limit]})


@space_bp.get('/summary')
@rate_limit(300, 3600)
def api_space2_summary():
    """GET /api/space2/summary — próximo lanzamiento, conteos por semana/mes y
    proveedor, plataformas activas y empresas del grafo implicadas."""
    up, s_up = get_launches('upcoming')
    prev, s_prev = get_launches('previous')
    out = summarize(up, prev)
    out['sources'] = {'upcoming': s_up, 'previous': s_prev}
    return jsonify(out)
