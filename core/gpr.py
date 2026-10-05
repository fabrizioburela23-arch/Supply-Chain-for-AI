"""core/gpr.py — Índice de RIESGO GEOPOLÍTICO (GPR) de Caldara & Iacoviello (Junta de la
Reserva Federal), EN VIVO y gratuito: https://www.matteoiacoviello.com/gpr.htm

Qué es: cuenta, cada día, la proporción de artículos de 10 grandes diarios que hablan de
tensiones geopolíticas (guerras, amenazas militares, terrorismo, tensiones nucleares).
100 = el promedio 1985-2019. Es un índice ACADÉMICO, muy citado por bancos centrales; mide
el riesgo PERCIBIDO en la prensa, no víctimas ni probabilidades.

  diario   → data_gpr_daily_recent.xls  (GPRD + medias 7/30 días)
  mensual  → data_gpr_export.xls        (GPR global y GPRC_<ISO3> por país)

Se publica solo en Excel (.xls) → requiere `xlrd`. Caché 12 h; si la fuente falla se
dice por qué (nunca se inventa un valor).
"""
import io
import logging
import os
import threading
import time
from datetime import datetime, timedelta

import requests

log = logging.getLogger('world')

DAILY_URL = 'https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls'
MONTHLY_URL = 'https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls'
TTL = 12 * 3600
_CACHE = {'data': None, 'ts': 0.0, 'error': None}
_LOCK = threading.Lock()

# ISO3 → clave de país del catálogo (core/world._COUNTRY) para cruzar con las empresas
ISO3_KEY = {'CHN': 'China', 'TWN': 'Taiwan', 'RUS': 'Rusia', 'UKR': 'Ucrania', 'ISR': 'Israel', 'KOR': 'Corea',
            'JPN': 'Japon', 'IND': 'India', 'MEX': 'Mexico', 'USA': 'EEUU', 'DEU': 'Alemania', 'NLD': 'PaisesBajos',
            'GBR': 'ReinoUnido', 'FRA': 'Francia', 'SAU': 'ArabiaSaudita', 'TUR': 'Turquia', 'BRA': 'Brasil',
            'CAN': 'Canada', 'AUS': 'Australia', 'ITA': 'Italia', 'ESP': 'Espana', 'SWE': 'Suecia', 'CHE': 'Suiza',
            'POL': 'Polonia', 'IDN': 'Indonesia', 'MYS': 'Malasia', 'PHL': 'Filipinas', 'THA': 'Tailandia',
            'VNM': 'Vietnam', 'EGY': 'Egipto', 'ZAF': 'Sudafrica', 'ARG': 'Argentina', 'COL': 'Colombia',
            'VEN': 'Venezuela', 'CHL': 'Chile', 'PER': 'Peru', 'NOR': 'Noruega', 'FIN': 'Finlandia', 'BEL': 'Belgica',
            'DNK': 'Dinamarca', 'PRT': 'Portugal', 'HUN': 'Hungria', 'TUN': 'Tunez'}
ISO3_ES = {'CHN': 'China', 'TWN': 'Taiwán', 'RUS': 'Rusia', 'UKR': 'Ucrania', 'ISR': 'Israel', 'KOR': 'Corea del Sur',
           'JPN': 'Japón', 'IND': 'India', 'MEX': 'México', 'USA': 'EE.UU.', 'DEU': 'Alemania', 'NLD': 'Países Bajos',
           'GBR': 'Reino Unido', 'FRA': 'Francia', 'SAU': 'Arabia Saudita', 'TUR': 'Turquía', 'BRA': 'Brasil'}


def _xls_rows(content):
    import xlrd   # noqa: PLC0415 — opcional
    book = xlrd.open_workbook(file_contents=content)
    sh = book.sheet_by_index(0)
    rows = [sh.row_values(i) for i in range(sh.nrows)]
    return rows, book.datemode


def _header(rows, must):
    for i, r in enumerate(rows[:10]):
        names = [str(c).strip() for c in r]
        if must in names:
            return i, {n: j for j, n in enumerate(names) if n}
    raise ValueError(f'bad_payload:gpr_header_{must}')


def _date_of(v, datemode):
    """Fecha en GPR: número YYYYMMDD, serial de Excel o texto."""
    try:
        f = float(v)
        if f > 19000000:
            return datetime.strptime(str(int(f)), '%Y%m%d')
        if f > 10000:
            import xlrd   # noqa: PLC0415
            return xlrd.xldate_as_datetime(f, datemode)
    except (TypeError, ValueError):
        pass
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%Y-%m', '%Y%m%d'):
        try:
            return datetime.strptime(str(v).strip()[:10], fmt)
        except ValueError:
            continue
    return None


def _num(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def parse_daily(rows, datemode=0):
    hi, col = _header(rows, 'GPRD')
    dcols = [col[k] for k in ('DAY', 'date', 'Date', 'day') if k in col]
    pts = []
    for r in rows[hi + 1:]:
        d = next((x for x in (_date_of(r[c], datemode) for c in dcols if str(r[c]).strip()) if x), None)
        v = _num(r[col['GPRD']])
        if d and v is not None:
            pts.append((d, v))
    if not pts:
        raise ValueError('bad_payload:gpr_daily_empty')
    pts.sort()
    last_d, last_v = pts[-1]
    win = lambda days: [v for d, v in pts if d > last_d - timedelta(days=days)]   # noqa: E731
    w7, w30, w365 = win(7), win(30), win(365)
    pct = round(100.0 * sum(1 for v in w365 if v <= last_v) / len(w365)) if w365 else None
    avg = lambda xs: round(sum(xs) / len(xs), 1) if xs else None   # noqa: E731
    return {'date': last_d.strftime('%Y-%m-%d'), 'value': round(last_v, 1), 'avg7': avg(w7), 'avg30': avg(w30),
            'avg365': avg(w365), 'percentile_1y': pct,
            'history': [{'date': d.strftime('%Y-%m-%d'), 'value': round(v, 1)} for d, v in pts[-120:]]}


def parse_monthly(rows, datemode=0):
    hi, col = _header(rows, 'GPR')
    dcol = next((col[k] for k in ('month', 'Month', 'date', 'DATE') if k in col), 0)
    data = []
    for r in rows[hi + 1:]:
        d = _date_of(r[dcol], datemode)
        if d and _num(r[col['GPR']]) is not None:
            data.append((d, r))
    if not data:
        raise ValueError('bad_payload:gpr_monthly_empty')
    data.sort(key=lambda x: x[0])
    last_d, last = data[-1]
    prev12 = [r for d, r in data[-13:-1]]
    countries = []
    for name, j in col.items():
        if not name.startswith('GPRC_'):
            continue
        iso = name[5:]
        v = _num(last[j])
        hist = [x for x in (_num(r[j]) for r in prev12) if x is not None]
        if v is None:
            continue
        base = sum(hist) / len(hist) if hist else None
        countries.append({'iso3': iso, 'country_key': ISO3_KEY.get(iso), 'name_es': ISO3_ES.get(iso, iso),
                          'value': round(v, 3), 'avg12m': round(base, 3) if base else None,
                          'vs_12m': round(v / base, 2) if base else None})
    countries.sort(key=lambda c: -(c['vs_12m'] or 0))
    return {'month': last_d.strftime('%Y-%m'), 'global': round(_num(last[col['GPR']]), 1), 'countries': countries}


def _get(url):
    r = requests.get(url, timeout=20, headers={'User-Agent': 'KhipuFinance/1.0 (+world-monitor)'})
    if r.status_code != 200:
        raise IOError(f'http:{r.status_code}')
    return r.content


def gpr_cached():
    """Lo que haya en caché (sin red): para el MCP y la mezcla con las capas de países."""
    d = _CACHE['data']
    return d if d and d.get('ok') else None


def gpr(force=False):
    """{ok, daily{…}, monthly{…}|None, source, url, as_of} o {ok: False, error_code…}. Caché 12 h."""
    now = time.time()
    with _LOCK:
        if _CACHE['data'] and not force and now - _CACHE['ts'] < TTL:
            return _CACHE['data']
    try:
        import xlrd  # noqa: F401,PLC0415
    except ImportError:
        return {'ok': False, 'error_code': 'missing_dependency', 'error_es': 'Falta el lector de Excel (xlrd) en el servidor.',
                'error_en': 'The Excel reader (xlrd) is missing on the server.'}
    out = {'ok': True, 'source': 'Caldara & Iacoviello GPR index (Federal Reserve Board)', 'url': 'https://www.matteoiacoviello.com/gpr.htm',
           'scale_es': '100 = promedio 1985-2019', 'scale_en': '100 = 1985-2019 average'}
    try:
        rows, dm = _xls_rows(_get(os.environ.get('WORLD_GPR_DAILY_URL') or DAILY_URL))
        out['daily'] = parse_daily(rows, dm)
    except Exception as e:  # noqa: BLE001
        log.info('gpr daily: %s', e)
        prev = _CACHE['data']
        if prev and prev.get('ok'):
            return dict(prev, stale=True)
        return {'ok': False, 'error_code': 'source_unavailable', 'error_es': f'El índice GPR no respondió ({str(e)[:80]}).',
                'error_en': f'The GPR index did not respond ({str(e)[:80]}).'}
    try:
        rows, dm = _xls_rows(_get(os.environ.get('WORLD_GPR_MONTHLY_URL') or MONTHLY_URL))
        out['monthly'] = parse_monthly(rows, dm)
    except Exception as e:  # noqa: BLE001
        log.info('gpr monthly: %s', e)
        out['monthly'] = None
    out['as_of'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    with _LOCK:
        _CACHE.update(data=out, ts=now)
    return out
