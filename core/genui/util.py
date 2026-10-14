"""core/genui/util.py — ayudantes PUROS de los constructores de bloques (sin E/S, sin IA, solo biblioteca estándar):
fechas al formato del contrato, ids de fuente, entidades, rótulos bilingües y números legibles para los `alt`.
"""
import math
import re
from datetime import datetime, timezone

_DT_OK = re.compile(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}([T ][0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]+)?)?'
                    r'(Z|[+-][0-9]{2}:?[0-9]{2})?)?$')
_GDELT = re.compile(r'^(\d{4})(\d{2})(\d{2})T?(\d{2})(\d{2})(\d{2})Z?$')
_ENTITY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.&'+-]{0,63}$")
_SOURCE_ID = re.compile(r'^[a-z][a-z0-9_.:-]{1,40}$')


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def norm_dt(v):
    """Fecha u hora → texto que cumple DateOrDateTime del contrato, o None (nunca se inventa una fecha).
    Acepta ISO (con o sin zona), 'YYYYMMDDTHHMMSSZ' (GDELT) y segundos unix."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        if not math.isfinite(float(v)) or v <= 0:
            return None
        try:
            return datetime.fromtimestamp(float(v), timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        except (OverflowError, OSError, ValueError):
            return None
    s = str(v).strip()[:40]
    if not s:
        return None
    if _DT_OK.match(s):
        return s
    m = _GDELT.match(s)
    if m:
        y, mo, d, h, mi, se = m.groups()
        return f'{y}-{mo}-{d}T{h}:{mi}:{se}Z'
    try:
        d = datetime.fromisoformat(s.replace('Z', '+00:00'))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        return None


_SRC_RULES = (
    ('prices_eod', 'prices_eod'), ('yahoo', 'yahoo'), ('finnhub', 'finnhub'), ('marketstack', 'marketstack'),
    ('fmp', 'fmp'), ('alpha vantage', 'alphavantage'), ('alphavantage', 'alphavantage'), ('gdelt', 'gdelt'),
    ('usgs', 'usgs'), ('eonet', 'eonet'), ('gdacs', 'gdacs'), ('portwatch', 'portwatch'),
    ('federal register', 'fedreg'), ('ofac', 'ofac'), ('cloudflare', 'cloudflare'), ('tavily', 'web'),
    ('world monitor', 'world_monitor'), ('kernel', 'hot_kernel'), ('research', 'research'),
    ('committee', 'committee'), ('launch library', 'll2'), ('celestrak', 'celestrak'), ('sec', 'sec'),
    ('grafo', 'khipus_graph'), ('graph', 'khipus_graph'), ('catalog', 'khipus_graph'),
)


def src_id(label, default='khipus'):
    """Nombre de fuente legible ('Yahoo Finance (live quotes…)', 'yahoo_live') → id del contrato ('yahoo')."""
    s = str(label or '').strip().lower()
    if _SOURCE_ID.match(s) and s not in ('yahoo_live',):
        for k, v in _SRC_RULES:
            if s == k.replace(' ', '_'):
                return v
        if s.startswith('yahoo'):
            return 'yahoo'
        return s
    for k, v in _SRC_RULES:
        if k in s:
            return v
    slug = re.sub(r'[^a-z0-9_.:-]+', '_', s).strip('_')[:40]
    return slug if _SOURCE_ID.match(slug or '') else default


def entity(eid, label=None, symbol=None):
    """Entity del contrato o None (un id que no cumple el patrón no se manda: el bloque lo omite)."""
    if not isinstance(eid, str) or not _ENTITY_ID.match(eid):
        return None
    lab = str(label or eid).strip()[:80] or eid[:80]
    out = {'id': eid, 'label': lab}
    if symbol:
        sym = str(symbol).strip()[:20]
        if sym:
            out['symbol'] = sym
    return out


def i18n(es, en=None):
    es = clip(es, 400)
    en = clip(en if en is not None else es, 400)
    return {'es': es or '—', 'en': en or es or '—'}


def clip(s, n):
    s = re.sub(r'\s+', ' ', str(s or '')).strip()
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def num(v):
    """Número finito (int/float, no bool) o None."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return v if math.isfinite(float(v)) else None
    return None


def fmt(v, lang='es', nd=None):
    """Número legible para un `alt` (lo escribe el servidor con el valor del bloque, no la IA): hasta 2 decimales,
    sin ceros de relleno ('41,2', '6', '4.447,3'), separadores es/en."""
    v = num(v)
    if v is None:
        return '—'
    s = f'{abs(v):,.{(2 if abs(v) >= 1 or v == 0 else 4) if nd is None else nd}f}'
    if nd is None and '.' in s:
        s = s.rstrip('0').rstrip('.')
    if lang == 'es':
        s = s.replace(',', '\u0001').replace('.', ',').replace('\u0001', '.')
    return ('−' if v < 0 else '') + s


def fmt_unit(v, unit, lang='es', currency=None):
    """'182,40 USD' · '−1,2 %' · '4.470 mil millones USD' · '37' (NRS)."""
    if num(v) is None:
        return '—'
    es = lang == 'es'
    if unit == 'pct':
        return fmt(v, lang) + ' %'
    if unit == 'pp':
        return fmt(v, lang) + ' pp'
    if unit == 'USD':
        return fmt(v, lang) + ' USD'
    if unit == 'CCY':
        return fmt(v, lang) + ' ' + (currency or '')
    if unit == 'USD_B':
        return fmt(v, lang) + (' mil millones USD' if es else ' billion USD')
    if unit == 'USD_T':
        return fmt(v, lang) + (' billones USD' if es else ' trillion USD')
    if unit == 'x':
        return fmt(v, lang) + '×'
    return fmt(v, lang)


def lttb(points, n):
    """Largest-Triangle-Three-Buckets: reduce [(x_idx, (fecha, y))…] a ≤ n puntos ELIGIENDO puntos que existen
    (la procedencia sigue valiendo: cada punto del bloque está en el resultado). points = [[fecha, y], …]."""
    m = len(points)
    if n >= m or n < 3:
        return list(points)
    ys = [p[1] if num(p[1]) is not None else 0.0 for p in points]
    out = [points[0]]
    every = (m - 2) / (n - 2)
    a = 0
    for i in range(n - 2):
        s = int(math.floor((i + 1) * every)) + 1
        e = min(int(math.floor((i + 2) * every)) + 1, m)
        if s >= e:
            s = min(s, m - 1)
            e = min(s + 1, m)
        avg_x = (s + e - 1) / 2.0
        avg_y = sum(ys[s:e]) / max(1, e - s)
        rs = int(math.floor(i * every)) + 1
        re_ = int(math.floor((i + 1) * every)) + 1
        best, best_area = rs, -1.0
        for j in range(rs, min(re_, m - 1)):
            area = abs((a - avg_x) * (ys[j] - ys[a]) - (a - j) * (avg_y - ys[a]))
            if area > best_area:
                best_area, best = area, j
        out.append(points[best])
        a = best
    out.append(points[-1])
    return out
