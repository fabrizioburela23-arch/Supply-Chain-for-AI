"""core/company_data.py — estados financieros anuales y perfil EN VIVO de
cualquier empresa cotizada del mundo (Dossier, 2026-09-28).

Pedido de Fabrizio: "que todas las empresas tengan dossier y que la info se
actualice en vivo". Antes:
  · /api/dossier usaba FMP /api/v3 → el plan de producción responde 402 y el
    cliente caía SIEMPRE a un dossier INVENTADO con Math.random().
  · /api/findossier probaba FMP → Alpha Vantage (solo EE.UU., 25 req/día):
    fuera de EE.UU. (Tokio, HK, Europa…) casi nunca había datos.

Ahora hay UNA cascada honesta, compartida por ambas rutas:
    FMP /stable/  →  Yahoo fundamentals-timeseries  →  Alpha Vantage
Yahoo cubre prácticamente todas las bolsas del mundo sin clave. NADA se
inventa: si ninguna fuente tiene el dato, la respuesta es {available: False}
con la razón (qué fuentes se probaron y por qué fallaron).

MONEDA: todos los montos salen en USD, convertidos con el tipo de cambio
ACTUAL de core.quotes._fx_to_usd (moneda del reporte → USD). Es la misma
convención que el resto de la app (todo en USD); los ratios (márgenes, ROE,
dilución) no dependen del tipo de cambio. `currency` conserva la moneda
original del reporte para que la UI pueda decirlo.

Diseño: funciones PURAS de transformación (payload crudo → dict normalizado,
testeables sin red) + funciones de red delgadas (_get_json, _yahoo_get) que
los tests reemplazan con monkeypatch.
"""
import copy
import logging
import os
import re
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import quote as _urlquote

import requests

from core import quotes as _q
from core.config import FINNHUB as _FINNHUB_DEFAULT

log = logging.getLogger('khipu')

FMP_KEY = os.getenv('FMP_KEY', '')
AV_KEY = os.getenv('AV_KEY') or os.getenv('ALPHA_VANTAGE_KEY', '')

TIMEOUT = 8
_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')

# ── Cachés en memoria (1 worker de gunicorn → un solo proceso, ver CLAUDE.md) ──
FIN_TTL_OK = 12 * 3600       # estados anuales completos: cambian 1 vez al año
FIN_TTL_PARTIAL = 3600       # parcial (p.ej. falta FCF): reintentar en 1 h
FIN_TTL_FAIL = 10 * 60       # fallo: NUNCA más de 10 min (puede ser transitorio)
LIVE_TTL_OK = 90             # perfil en vivo: la UI refresca cada 60 s
LIVE_TTL_FAIL = 60
_CACHE_MAX = 800
_FIN_CACHE = {}    # ticker → (ts, data, ttl)
_LIVE_CACHE = {}   # ticker → (ts, data, ttl)
# Un candado por ticker: si fincard + terminal piden la MISMA empresa a la vez
# (8 threads de gunicorn), solo uno sale a la red y el otro lee la caché —
# importa sobre todo para Alpha Vantage (25 req/día).
_LOCKS = {}
_LOCKS_GUARD = threading.Lock()

# AV free = 1 request/segundo: pausa entre sus 3 llamadas (reemplazable en tests)
_sleep = time.sleep

_PERIOD1 = 1483228800        # 2017-01-01 00:00 UTC
_Y_TS_URL = 'https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{sym}'
_Y_QS_URL = 'https://query2.finance.yahoo.com/v10/finance/quoteSummary/{sym}'
_Y_CHART_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/{sym}'
_Y_QS_MODULES = 'price,summaryProfile,financialData,defaultKeyStatistics,summaryDetail'
_FMP_BASE = 'https://financialmodelingprep.com/stable/'
_AV_URL = 'https://www.alphavantage.co/query'
_FH_BASE = 'https://finnhub.io/api/v1/'

# Tipos de Yahoo fundamentals-timeseries → campo normalizado
_Y_TYPES = {
    'annualTotalRevenue': 'revenue',
    'annualGrossProfit': 'gross_profit',
    'annualNetIncome': 'net_income',
    'annualNetIncomeCommonStockholders': 'net_income_common',
    'annualFreeCashFlow': 'fcf',
    'annualOperatingCashFlow': 'ocf',
    'annualCapitalExpenditure': 'capex',
    'annualTotalDebt': 'total_debt',
    'annualCashAndCashEquivalents': 'cash',
    'annualStockholdersEquity': 'equity',
    'annualDilutedAverageShares': 'shares_diluted',
    'annualOrdinarySharesNumber': 'shares_ordinary',
    'annualEBITDA': 'ebitda',
    'annualDilutedEPS': 'eps',
    'annualOperatingIncome': 'operating_income',
    'annualInvestedCapital': 'invested_capital',
    'annualTaxRateForCalcs': 'tax_rate',
}
# Campos que NO son dinero (no se convierten a USD)
_NOT_MONEY = {'shares', 'shares_diluted', 'shares_ordinary', 'tax_rate',
              'roe', 'roic', 'ev_to_sales', 'pe'}

# Campos de la estructura normalizada (listas alineadas con `years`)
_FIELDS = ('revenue', 'gross_profit', 'net_income', 'fcf', 'total_debt', 'cash',
           'equity', 'shares', 'ebitda', 'eps', 'ev_to_sales',
           # extras (no rompen el contrato): capex (USD, negativo = gasto),
           # operating_income, invested_capital (USD), roe/roic (FRACCIÓN),
           # pe (múltiplo, solo si la fuente lo da)
           'capex', 'operating_income', 'invested_capital', 'roe', 'roic', 'pe')
_SCORE_FIELDS = ('revenue', 'gross_profit', 'net_income', 'fcf', 'total_debt',
                 'cash', 'equity', 'shares', 'ebitda', 'eps')

# Monedas de "unidad menor" que usa Yahoo para el PRECIO (peniques, centavos)
_MINOR = {'GBp': ('GBP', 0.01), 'GBX': ('GBP', 0.01), 'ZAc': ('ZAR', 0.01),
          'ZAC': ('ZAR', 0.01), 'ILA': ('ILS', 0.01)}

_SRC_LABEL = {'fmp': 'FMP', 'yahoo': 'Yahoo Finance', 'alphavantage': 'Alpha Vantage',
              'finnhub': 'Finnhub', 'yahoo_chart': 'Yahoo Finance (chart)'}


# ════════════════════════════════════════════════════════════════════════════
# Helpers puros
# ════════════════════════════════════════════════════════════════════════════

def _num(v):
    """Número o None. Acepta {'raw': x, 'fmt': …} (Yahoo), strings numéricas
    (Alpha Vantage, que usa 'None' para vacío) y descarta NaN/inf/bool."""
    if isinstance(v, dict):
        v = v.get('raw')
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float('inf'), float('-inf')):
        return None
    return f


def _str(v):
    """String limpio o None (Yahoo a veces manda {'raw':…} o '')."""
    if isinstance(v, dict):
        v = v.get('raw') if 'raw' in v else v.get('fmt')
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _major(cur):
    """Código ISO de la moneda 'mayor' ('GBp' → 'GBP'); None si vacío."""
    if not cur:
        return None
    cur = str(cur).strip()
    if cur in _MINOR:
        return _MINOR[cur][0]
    return cur.upper()


def _usd_rate(cur, fx=None):
    """Tasa cur→USD, consciente de unidades menores ('GBp' = GBP/100).
    `fx` = función código ISO mayor → tasa (por defecto core.quotes._fx_to_usd,
    resuelta en cada llamada para que los tests puedan reemplazarla).
    None si no hay tasa (no se inventa)."""
    if not cur:
        return None
    cur = str(cur).strip()
    base, factor = _MINOR.get(cur, (cur.upper(), 1.0))
    try:
        r = (fx or _q._fx_to_usd)(base)
    except Exception:  # noqa: BLE001
        r = None
    return r * factor if r else None


def _round(v, nd):
    return round(v, nd) if v is not None else None


def _pct(v, nd=2):
    """Fracción (0.253) → porcentaje (25.3)."""
    return round(v * 100, nd) if v is not None else None


def _now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _has(lst):
    return any(v is not None for v in (lst or []))


def _consecutive(y_prev, y):
    """¿Años fiscales consecutivos? (un hueco no debe leerse como 'crecimiento anual')."""
    try:
        return int(y) - int(y_prev) == 1
    except (TypeError, ValueError):
        return False


def _derive(row):
    """Completa, con aritmética sobre datos REALES del mismo año, lo que la
    fuente no reporta directo: FCF = OCF + CapEx (CapEx viene negativo),
    ROE = utilidad neta / patrimonio, ROIC = EBIT·(1−tasa) / capital invertido.
    Patrimonio o capital invertido ≤ 0 → ratio sin sentido → None."""
    if row.get('fcf') is None and row.get('ocf') is not None and row.get('capex') is not None:
        row['fcf'] = row['ocf'] - abs(row['capex'])
    if row.get('net_income') is None and row.get('net_income_common') is not None:
        row['net_income'] = row['net_income_common']
    eq = row.get('equity')
    if row.get('roe') is None and row.get('net_income') is not None and eq is not None and eq > 0:
        row['roe'] = row['net_income'] / eq
    ic, oi, tax = row.get('invested_capital'), row.get('operating_income'), row.get('tax_rate')
    if (row.get('roic') is None and oi is not None and ic is not None and ic > 0
            and tax is not None and 0 <= tax <= 1):
        row['roic'] = oi * (1 - tax) / ic
    return row


def _empty_fin(reason=None, reason_en=None, currency=None):
    out = {'available': False, 'source': None, 'currency': currency,
           'reason': reason, 'reason_en': reason_en, 'years': []}
    for f in _FIELDS:
        out[f] = []
    return out


def _assemble(by_year, source, currency, max_years=6, fx_rate=None):
    """{año: {campo: valor}} → estructura normalizada con listas alineadas.
    Solo entran los años con algún dato de resultados (ingresos, utilidad o
    FCF): un año con solo balance daría columnas vacías."""
    years = sorted(y for y, r in by_year.items()
                   if any(r.get(k) is not None for k in ('revenue', 'net_income', 'fcf')))[-max_years:]
    if not years:
        return _empty_fin('sin datos', 'no data', currency)
    out = {'available': True, 'source': source, 'currency': currency,
           'reason': None, 'reason_en': None, 'years': years}
    for f in _FIELDS:
        out[f] = [by_year[y].get(f) for y in years]
    if fx_rate is not None:
        out['fx_rate'] = fx_rate   # tasa usada (moneda del reporte → USD, tipo de cambio actual)
    return out


def _dominant(counter):
    return counter.most_common(1)[0][0] if counter else None


class _Converter:
    """Convierte montos a USD por moneda, memoizando la tasa por moneda."""

    def __init__(self, fx, default_cur):
        self.fx = fx               # código ISO mayor → tasa (None = core.quotes)
        self.default = default_cur
        self.rates = {}

    def rate(self, cur):
        cur = cur or self.default
        if not cur:
            return None
        if cur not in self.rates:
            self.rates[cur] = _usd_rate(cur, self.fx)
        return self.rates[cur]

    def __call__(self, v, cur=None):
        if v is None:
            return None
        r = self.rate(cur)
        return v * r if r is not None else None


# ── Yahoo fundamentals-timeseries ────────────────────────────────────────────

def _yahoo_series(payload):
    """payload crudo → {tipo: {año: (valor, moneda, asOfDate)}}. Si hay dos
    entradas del mismo año (cambio de cierre fiscal) gana la más reciente."""
    out = {}
    results = (((payload or {}).get('timeseries') or {}).get('result') or [])
    for item in results:
        if not isinstance(item, dict):
            continue
        typ = ((item.get('meta') or {}).get('type') or [None])[0]
        if not typ:
            continue
        for e in item.get(typ) or []:
            if not isinstance(e, dict):
                continue            # Yahoo rellena con null los años sin dato
            d = str(e.get('asOfDate') or '')
            y = d[:4]
            if not y.isdigit():
                continue
            v = _num(e.get('reportedValue'))
            if v is None:
                continue
            slot = out.setdefault(typ, {})
            if y not in slot or d > slot[y][2]:
                slot[y] = (v, e.get('currencyCode'), d)
    return out


def yahoo_timeseries_to_annual(payload, fx=None, max_years=6):
    """Payload de Yahoo fundamentals-timeseries → estructura normalizada (USD).
    Función PURA salvo `fx` (cur → tasa USD; por defecto core.quotes)."""
    ser = _yahoo_series(payload)
    if not ser:
        return _empty_fin('sin datos', 'no data')
    curs = Counter()
    for typ in ('annualTotalRevenue', 'annualNetIncome', 'annualOperatingCashFlow',
                'annualStockholdersEquity'):
        for (_v, c, _d) in ser.get(typ, {}).values():
            if c:
                curs[c] += 1
    cur = _dominant(curs)
    conv = _Converter(fx, cur)
    if cur and conv.rate(cur) is None:
        return _empty_fin(f'sin tipo de cambio {cur}→USD', f'no {cur}→USD exchange rate', cur)
    by_year = {}
    for typ, field in _Y_TYPES.items():
        for y, (v, c, _d) in ser.get(typ, {}).items():
            row = by_year.setdefault(y, {})
            row[field] = v if field in _NOT_MONEY else conv(v, c)
    # Acciones: UNA serie consistente (mezclar diluidas y ordinarias año a año
    # fabricaría "dilución" falsa). Diluidas promedio si cubren igual o más.
    n_dil = sum(1 for r in by_year.values() if r.get('shares_diluted') is not None)
    n_ord = sum(1 for r in by_year.values() if r.get('shares_ordinary') is not None)
    sh_key = 'shares_diluted' if n_dil >= n_ord else 'shares_ordinary'
    for r in by_year.values():
        r['shares'] = r.get(sh_key)
        _derive(r)
    return _assemble(by_year, 'yahoo', cur, max_years, fx_rate=conv.rate(cur) if cur else None)


# ── FMP /stable/ ─────────────────────────────────────────────────────────────

def _fmp_year(r):
    y = str(r.get('fiscalYear') or r.get('calendarYear') or '')[:4]
    if not y.isdigit():
        y = str(r.get('date') or '')[:4]
    return y if y.isdigit() else None


def _fmp_index(rows):
    out = {}
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict):
            continue
        y = _fmp_year(r)
        if y and (y not in out or str(r.get('date', '')) > str(out[y].get('date', ''))):
            out[y] = r
    return out


def _first(d, *keys):
    for k in keys:
        v = _num(d.get(k))
        if v is not None:
            return v
    return None


def fmp_statements_to_annual(inc, cfs, bal, km, fx=None, max_years=6):
    """Estados anuales de FMP (stable o v3) → estructura normalizada (USD)."""
    yi, yc, yb, yk = _fmp_index(inc), _fmp_index(cfs), _fmp_index(bal), _fmp_index(km)
    if not yi:
        return _empty_fin('sin datos', 'no data')
    cur = _dominant(Counter(r.get('reportedCurrency') for r in yi.values() if r.get('reportedCurrency')))
    cur = cur or 'USD'   # FMP omite reportedCurrency solo en emisores de EE.UU.
    conv = _Converter(fx, cur)
    if conv.rate(cur) is None:
        return _empty_fin(f'sin tipo de cambio {cur}→USD', f'no {cur}→USD exchange rate', cur)
    sh_key = ('weightedAverageShsOutDil'
              if any(_num(r.get('weightedAverageShsOutDil')) for r in yi.values())
              else 'weightedAverageShsOut')
    by_year = {}
    for y, i in yi.items():
        c, b, k = yc.get(y, {}), yb.get(y, {}), yk.get(y, {})
        ci = i.get('reportedCurrency') or cur
        cc = c.get('reportedCurrency') or ci
        cb = b.get('reportedCurrency') or ci
        by_year[y] = _derive({
            'revenue': conv(_num(i.get('revenue')), ci),
            'gross_profit': conv(_num(i.get('grossProfit')), ci),
            'net_income': conv(_num(i.get('netIncome')), ci),
            'ebitda': conv(_num(i.get('ebitda')), ci),
            'eps': conv(_first(i, 'epsDiluted', 'epsdiluted', 'eps'), ci),
            'operating_income': conv(_num(i.get('operatingIncome')), ci),
            'shares': _num(i.get(sh_key)),
            'fcf': conv(_num(c.get('freeCashFlow')), cc),
            'ocf': conv(_first(c, 'operatingCashFlow', 'netCashProvidedByOperatingActivities'), cc),
            'capex': conv(_num(c.get('capitalExpenditure')), cc),
            'total_debt': conv(_num(b.get('totalDebt')), cb),
            'cash': conv(_num(b.get('cashAndCashEquivalents')), cb),
            'equity': conv(_first(b, 'totalStockholdersEquity', 'totalEquity'), cb),
            'roe': _first(k, 'returnOnEquity', 'roe'),
            'roic': _first(k, 'returnOnInvestedCapital', 'roic'),
            'ev_to_sales': _first(k, 'evToSales', 'enterpriseValueOverRevenue', 'evToRevenue'),
            'pe': _first(k, 'peRatio'),
        })
    return _assemble(by_year, 'fmp', cur, max_years, fx_rate=conv.rate(cur))


# ── Alpha Vantage ────────────────────────────────────────────────────────────

def _av_index(rows):
    out = {}
    for r in rows if isinstance(rows, list) else []:
        if isinstance(r, dict):
            y = str(r.get('fiscalDateEnding') or '')[:4]
            if y.isdigit() and y not in out:
                out[y] = r
    return out


def av_reports_to_annual(inc, bal, cfs, fx=None, max_years=6):
    """annualReports de Alpha Vantage (INCOME_STATEMENT, BALANCE_SHEET,
    CASH_FLOW) → estructura normalizada (USD). AV reporta capex POSITIVO."""
    yi, yb, yc = _av_index(inc), _av_index(bal), _av_index(cfs)
    if not yi:
        return _empty_fin('sin datos', 'no data')
    cur = _dominant(Counter(r.get('reportedCurrency') for r in yi.values() if r.get('reportedCurrency'))) or 'USD'
    conv = _Converter(fx, cur)
    if conv.rate(cur) is None:
        return _empty_fin(f'sin tipo de cambio {cur}→USD', f'no {cur}→USD exchange rate', cur)
    by_year = {}
    for y, i in yi.items():
        b, c = yb.get(y, {}), yc.get(y, {})
        ci = i.get('reportedCurrency') or cur
        capex = _num(c.get('capitalExpenditures'))
        by_year[y] = _derive({
            'revenue': conv(_num(i.get('totalRevenue')), ci),
            'gross_profit': conv(_num(i.get('grossProfit')), ci),
            'net_income': conv(_num(i.get('netIncome')), ci),
            'ebitda': conv(_num(i.get('ebitda')), ci),
            'operating_income': conv(_num(i.get('operatingIncome')), ci),
            'shares': _num(b.get('commonStockSharesOutstanding')),
            'total_debt': conv(_num(b.get('shortLongTermDebtTotal')), b.get('reportedCurrency') or ci),
            'cash': conv(_first(b, 'cashAndCashEquivalentsAtCarryingValue', 'cashAndShortTermInvestments'),
                         b.get('reportedCurrency') or ci),
            'equity': conv(_num(b.get('totalShareholderEquity')), b.get('reportedCurrency') or ci),
            'ocf': conv(_num(c.get('operatingCashflow')), c.get('reportedCurrency') or ci),
            'capex': conv(-abs(capex) if capex is not None else None, c.get('reportedCurrency') or ci),
        })
    return _assemble(by_year, 'alphavantage', cur, max_years, fx_rate=conv.rate(cur))


# ════════════════════════════════════════════════════════════════════════════
# Red (delgada, reemplazable en tests)
# ════════════════════════════════════════════════════════════════════════════

def _get_json(url, params=None, timeout=TIMEOUT):
    """GET JSON. Devuelve (json, error). El error NUNCA incluye la URL: lleva la
    API key en la query y terminaría en el `reason` que ve el navegador."""
    try:
        r = requests.get(url, params=params, timeout=timeout, headers={'User-Agent': _UA})
    except requests.exceptions.Timeout:
        return None, 'timeout'
    except Exception as e:  # noqa: BLE001
        return None, type(e).__name__
    if r.status_code != 200:
        return None, f'upstream {r.status_code}'
    try:
        return r.json(), None
    except ValueError:
        return None, 'invalid json'


def _yahoo_get(url, params=None, timeout=TIMEOUT):
    """GET a Yahoo con la sesión + crumb compartidas de core.quotes. Si la crumb
    caducó (401/403) renueva la sesión UNA vez. Devuelve (json, error)."""
    for attempt in (0, 1):
        try:
            s, crumb = _q._yahoo_session()
            p = dict(params or {})
            if crumb:
                p['crumb'] = crumb
            r = s.get(url, params=p, timeout=timeout)
        except requests.exceptions.Timeout:
            return None, 'timeout'
        except Exception as e:  # noqa: BLE001
            return None, type(e).__name__
        if r.status_code in (401, 403) and attempt == 0:
            _q._Y_SESS['ts'] = 0          # fuerza sesión/crumb nuevas
            continue
        if r.status_code != 200:
            return None, f'upstream {r.status_code}'
        try:
            return r.json(), None
        except ValueError:
            return None, 'invalid json'
    return None, 'crumb'


def _sym(t):
    return _urlquote(t, safe='.-=')


def _fetch_fmp(t, key):
    errs = {}

    def get(res):
        data, err = _get_json(_FMP_BASE + res, {'symbol': t, 'limit': 6, 'apikey': key})
        if isinstance(data, list) and data:
            return data
        if isinstance(data, dict):
            errs[res] = str(data.get('Error Message') or data.get('message') or 'sin datos')[:150]
        else:
            errs[res] = err or 'sin datos'
        return []

    inc = get('income-statement')
    if not inc:
        return None, errs.get('income-statement') or 'sin datos'
    cfs = get('cash-flow-statement')
    bal = get('balance-sheet-statement')
    km = get('key-metrics')
    res = fmp_statements_to_annual(inc, cfs, bal, km)
    return (res, None) if res.get('available') else (None, _reason_pair(res))


def _fetch_yahoo_fin(t):
    params = {'symbol': t, 'type': ','.join(_Y_TYPES), 'period1': _PERIOD1,
              'period2': int(time.time())}
    data, err = _yahoo_get(_Y_TS_URL.format(sym=_sym(t)), params)
    if data is None:
        return None, err or 'sin datos'
    res = yahoo_timeseries_to_annual(data)
    return (res, None) if res.get('available') else (None, _reason_pair(res))


def _fetch_av(t, key):
    notes = []

    def av(fn):
        data, err = _get_json(_AV_URL, {'function': fn, 'symbol': t, 'apikey': key})
        if isinstance(data, dict):
            note = data.get('Note') or data.get('Information') or data.get('Error Message')
            if note:
                notes.append(str(note)[:160])
            return data.get('annualReports') or []
        if err:
            notes.append(err)
        return []

    inc = av('INCOME_STATEMENT')
    if not inc:
        return None, notes[0] if notes else 'sin datos'
    _sleep(1.2)
    bal = av('BALANCE_SHEET')
    _sleep(1.2)
    cfs = av('CASH_FLOW')
    res = av_reports_to_annual(inc, bal, cfs)
    return (res, None) if res.get('available') else (None, _reason_pair(res))


def _reason_pair(res):
    """Razón bilingüe (es, en) que ya trae una transformación pura (p.ej.
    'sin tipo de cambio JPY→USD'): se pasa tal cual a _explain como tupla."""
    res = res or {}
    return (res.get('reason') or 'sin datos', res.get('reason_en') or 'no data')


# Errores crudos de red → texto llano bilingüe. El código crudo ('upstream
# 404', 'timeout', 'ConnectionError'…) va SOLO al log: el usuario (no experto,
# ver CLAUDE.md) lee frases, no códigos.
_PLAIN = {
    'no_key': ('sin clave configurada', 'no key configured'),
    'us_only': ('solo cubre EE.UU.', 'US only'),
    'no_data': ('sin datos', 'no data'),
    'timeout': ('tardó demasiado en responder', 'took too long to answer'),
    'not_found': ('no reconoce este símbolo', 'does not recognize this symbol'),
    'rate': ('límite de consultas alcanzado, reintenta más tarde', 'query limit reached, try again later'),
    'plan': ('el plan contratado no incluye este dato', 'the current plan does not include this data'),
    'bad_key': ('la clave no es válida', 'the key is not valid'),
    'server': ('la fuente tuvo una falla temporal', 'the source had a temporary failure'),
    'unreadable': ('respondió algo que no se pudo leer', 'sent a reply that could not be read'),
    'denied': ('rechazó el acceso', 'denied access'),
    'connect': ('no se pudo conectar', 'could not connect'),
    'other': ('no respondió', 'did not answer'),
}


def _classify(err):
    """Código/mensaje crudo de una fuente → clave de _PLAIN."""
    e = str(err or '').strip()
    low = e.lower()
    if low in ('', 'sin datos', 'no data'):
        return 'no_data'
    if low in ('no_key', 'us_only'):
        return low
    if 'timeout' in low or 'timed out' in low:
        return 'timeout'
    if low.startswith('upstream '):
        code = low.split(' ', 1)[1].strip()
        if code == '404':
            return 'not_found'
        if code == '429':
            return 'rate'
        if code in ('402', '403'):
            return 'plan'
        if code == '401':
            return 'denied'
        if code.startswith('5'):
            return 'server'
        return 'other'
    if low == 'invalid json':
        return 'unreadable'
    if low == 'crumb':
        return 'denied'
    if 'connection' in low or 'ssl' in low or 'proxy' in low:
        return 'connect'
    # mensajes en prosa de FMP / Alpha Vantage (vienen en inglés)
    if 'rate limit' in low or 'requests per' in low or 'limit reach' in low or 'too many' in low:
        return 'rate'
    if 'api key' in low or 'apikey' in low:
        return 'bad_key'
    if ('premium' in low or 'subscription' in low or 'legacy' in low or 'upgrade' in low
            or re.search(r'\bplans?\b', low) or 'exclusive' in low
            or re.search(r'\b40[23]\b', low)):
        return 'plan'
    if 'invalid api call' in low or 'not found' in low or 'invalid ticker' in low or 'symbol' in low:
        return 'not_found'
    return 'other'


def _explain(src, err):
    """Error de una fuente → (texto es, texto en) para el `reason`.

    `err` es un código crudo de red o una tupla (es, en) que ya viene
    traducida desde una transformación pura. Nunca devuelve el código crudo."""
    lab = _SRC_LABEL.get(src, src)
    if isinstance(err, tuple) and len(err) == 2:
        es, en = err
        return f'{lab}: {es}', f'{lab}: {en}'
    kind = _classify(err)
    if kind in ('other', 'connect', 'server', 'unreadable', 'denied'):
        log.info('company_data %s: %s', src, str(err or '')[:160])   # el crudo, solo al log
    es, en = _PLAIN[kind]
    return f'{lab}: {es}', f'{lab}: {en}'


def _score(res):
    if not res or not res.get('available'):
        return 0
    return sum(1 for f in _SCORE_FIELDS if _has(res.get(f)))


def _complete(res):
    return all(_has(res.get(f)) for f in ('revenue', 'fcf', 'equity'))


def _better(res, best):
    """¿`res` es mejor que `best`? Primero la completitud (ingresos + FCF +
    patrimonio), y solo a igual completitud, la cantidad de campos."""
    return (_complete(res), _score(res)) > (_complete(best), _score(best))


def _cache_get(cache, key):
    e = cache.get(key)
    if e and time.time() - e[0] < e[2]:
        return copy.deepcopy(e[1])
    return None


def _cache_put(cache, key, data, ttl):
    if len(cache) > _CACHE_MAX:
        now = time.time()
        for k in [k for k, e in cache.items() if now - e[0] >= e[2]]:
            cache.pop(k, None)
        if len(cache) > _CACHE_MAX:
            cache.clear()
    cache[key] = (time.time(), copy.deepcopy(data), ttl)


def _lock_for(key):
    with _LOCKS_GUARD:
        lk = _LOCKS.get(key)
        if lk is None:
            if len(_LOCKS) > 4 * _CACHE_MAX:
                _LOCKS.clear()
            lk = _LOCKS[key] = threading.Lock()
        return lk


def _clear_caches():
    """Para tests."""
    _FIN_CACHE.clear()
    _LIVE_CACHE.clear()


# ════════════════════════════════════════════════════════════════════════════
# API pública del módulo
# ════════════════════════════════════════════════════════════════════════════

def get_annual_financials(ticker, fmp_key=None, av_key=None, use_cache=True):
    """Series anuales normalizadas (USD) de una empresa cotizada.

    Cascada honesta: FMP /stable/ → Yahoo fundamentals-timeseries → Alpha
    Vantage (solo EE.UU. y solo si nadie más dio datos: el plan gratis tiene
    25 req/día). Se queda con la primera fuente COMPLETA (ingresos + FCF +
    patrimonio); si ninguna lo es, con la que más datos trajo. NUNCA inventa.

    Devuelve {available, source, currency, reason, reason_en, tried, years,
    revenue, gross_profit, net_income, fcf, total_debt, cash, equity, shares,
    ebitda, eps, ev_to_sales, capex, operating_income, invested_capital,
    roe, roic, pe}. Listas alineadas con `years` (ascendente), None si falta.
    Montos en USD crudos; shares en acciones; roe/roic en FRACCIÓN.
    """
    t = (ticker or '').strip().upper()
    if not t:
        return _empty_fin('ticker vacío', 'empty ticker')
    if use_cache:
        hit = _cache_get(_FIN_CACHE, t)
        if hit is not None:
            return hit
    fmp = FMP_KEY if fmp_key is None else fmp_key
    av = AV_KEY if av_key is None else av_key
    with _lock_for('fin:' + t):
        if use_cache:              # otro thread pudo llenarla mientras esperábamos
            hit = _cache_get(_FIN_CACHE, t)
            if hit is not None:
                return hit
        return _compute_annual(t, fmp, av)


def _compute_annual(t, fmp, av):
    tried, notes_es, notes_en = [], [], []
    best = None

    def note(src, err):
        es, en = _explain(src, err)
        notes_es.append(es)
        notes_en.append(en)

    for src in ('fmp', 'yahoo', 'alphavantage'):
        if src == 'fmp':
            if not fmp:
                note('fmp', 'no_key')
                continue
            fetch = lambda: _fetch_fmp(t, fmp)  # noqa: E731
        elif src == 'yahoo':
            fetch = lambda: _fetch_yahoo_fin(t)  # noqa: E731
        else:
            if best is not None:
                break                   # AV (25/día) solo si nadie dio nada
            if not av:
                note('alphavantage', 'no_key')
                continue
            if _q.is_intl(t):
                note('alphavantage', 'us_only')
                continue
            fetch = lambda: _fetch_av(t, av)  # noqa: E731
        tried.append(src)
        try:
            res, err = fetch()
        except Exception as e:  # noqa: BLE001
            log.warning('company_data %s %s: %s', src, t, type(e).__name__)
            res, err = None, type(e).__name__
        if res and res.get('available'):
            # Completitud PRIMERO (ingresos + FCF + patrimonio), luego cantidad
            # de datos: una fuente completa con menos campos (p.ej. Yahoo sin
            # EBITDA en un banco) le gana a una parcial sin FCF (p.ej. FMP con
            # el cash-flow en 402/timeout) — si no, el FCF desaparece del
            # Dossier aunque una fuente sí lo trajo.
            if best is None or _better(res, best):
                best = res
            if _complete(best):
                break
        else:
            note(src, err)

    if best is not None:
        best['tried'] = tried
        best['reason'] = None
        best['reason_en'] = None
        _cache_put(_FIN_CACHE, t, best, FIN_TTL_OK if _complete(best) else FIN_TTL_PARTIAL)
        return copy.deepcopy(best)

    out = _empty_fin(
        f'Sin estados financieros públicos para {t} — ' + ' · '.join(notes_es),
        f'No public financial statements for {t} — ' + ' · '.join(notes_en))
    out['tried'] = tried
    _cache_put(_FIN_CACHE, t, out, FIN_TTL_FAIL)
    return out


# ── Transformaciones a las respuestas HTTP que ya consume el cliente ─────────

def to_findossier(fin, ticker):
    """Estructura normalizada → respuesta de /api/findossier, con EXACTAMENTE
    las claves/unidades que consumen engine/fincard.js, cockpit.js,
    termdata.js y localcharts.js: revenue/fcf/capex crudos en USD;
    revenue_growth, gross_margin, fcf_margin, fcf_growth, roe en %;
    dilution en % (2 decimales); shares en MILES DE MILLONES; de_ratio y
    ev_to_sales como múltiplos."""
    if not fin or not fin.get('available'):
        return {'available': False, 'ticker': ticker, 'source': None,
                'currency': (fin or {}).get('currency'),
                'reason': (fin or {}).get('reason') or 'sin datos',
                'reason_en': (fin or {}).get('reason_en') or 'no data',
                'tried': (fin or {}).get('tried', [])}
    years = fin['years']
    g = lambda k, i: (fin.get(k) or [None] * len(years))[i]  # noqa: E731
    s = {'years': [], 'revenue': [], 'revenue_growth': [], 'gross_margin': [],
         'capex': [], 'fcf': [], 'fcf_margin': [], 'fcf_growth': [], 'dilution': [],
         'de_ratio': [], 'roe': [], 'ev_to_sales': [], 'shares': []}
    prev_y = prev_rev = prev_fcf = prev_sh = None
    for i, y in enumerate(years):
        rev, gp, fcf, capex = g('revenue', i), g('gross_profit', i), g('fcf', i), g('capex', i)
        sh, debt, eq, roe, evs = g('shares', i), g('total_debt', i), g('equity', i), g('roe', i), g('ev_to_sales', i)
        cons = _consecutive(prev_y, y)
        s['years'].append(y)
        s['revenue'].append(rev)
        s['revenue_growth'].append(round((rev / prev_rev - 1) * 100, 1)
                                   if cons and rev is not None and prev_rev and prev_rev > 0 else None)
        s['gross_margin'].append(round(gp / rev * 100, 1) if gp is not None and rev and rev > 0 else None)
        s['capex'].append(abs(capex) if capex is not None else None)
        s['fcf'].append(fcf)
        s['fcf_margin'].append(round(fcf / rev * 100, 1) if fcf is not None and rev and rev > 0 else None)
        s['fcf_growth'].append(round((fcf / prev_fcf - 1) * 100, 1)
                               if cons and fcf is not None and prev_fcf and prev_fcf > 0 else None)
        s['dilution'].append(round((sh / prev_sh - 1) * 100, 2) if cons and sh and prev_sh else None)
        s['shares'].append(round(sh / 1e9, 3) if sh else None)
        s['de_ratio'].append(round(debt / eq, 3) if debt is not None and eq and eq > 0 else None)
        s['roe'].append(round(roe * 100, 1) if roe is not None else None)
        s['ev_to_sales'].append(round(evs, 1) if evs is not None else None)
        prev_y, prev_rev, prev_fcf, prev_sh = y, rev, fcf, sh
    return {'available': True, 'ticker': ticker, 'source': fin.get('source'),
            'currency': fin.get('currency'), 'reason': None, 'reason_en': None,
            'tried': fin.get('tried', []), **s}


def to_dossier(fin, ticker):
    """Estructura normalizada → respuesta de /api/dossier con las claves y
    unidades que consume app.html `_dossierRenderPanels`: MILES DE MILLONES USD
    (revenue, fcf, total_debt, cash, net_debt, net_income, ebitda), shares en
    miles de millones, % (revenue_growth, fcf_margin, gross_margin, net_margin,
    roe, roic), múltiplos (ev_revenue, pe_ratio), eps en USD.
    `synthetic` es SIEMPRE False: este servidor no inventa cifras."""
    if not fin or not fin.get('available'):
        return {'available': False, 'synthetic': False, 'ticker': ticker, 'source': None,
                'currency': (fin or {}).get('currency'),
                'reason': (fin or {}).get('reason') or 'sin datos',
                'reason_en': (fin or {}).get('reason_en') or 'no data',
                'tried': (fin or {}).get('tried', [])}
    years = fin['years']
    n = len(years)
    col = lambda k: list(fin.get(k) or [None] * n)  # noqa: E731
    B = lambda v: round(v / 1e9, 2) if v is not None else None  # noqa: E731
    rev, fcf, ni = col('revenue'), col('fcf'), col('net_income')
    gp, debt, cash = col('gross_profit'), col('total_debt'), col('cash')
    growth = [None]
    for i in range(1, n):
        a, b = rev[i - 1], rev[i]
        growth.append(round((b - a) / abs(a) * 100, 1)
                      if _consecutive(years[i - 1], years[i]) and a and b is not None else None)
    return {
        'available': True,
        'ticker': ticker,
        'years': years,
        'synthetic': False,
        'source': fin.get('source'),
        'currency': fin.get('currency'),
        'reason': None,
        'reason_en': None,
        'tried': fin.get('tried', []),
        'revenue': [B(v) for v in rev],
        'revenue_growth': growth,
        'shares': [round(v / 1e9, 3) if v else None for v in col('shares')],
        'fcf': [B(v) for v in fcf],
        'fcf_margin': [round(f / r * 100, 1) if f is not None and r and r > 0 else None
                       for f, r in zip(fcf, rev)],
        'ev_revenue': [_round(v, 2) for v in col('ev_to_sales')],
        'pe_ratio': [_round(v, 1) for v in col('pe')],
        'total_debt': [B(v) for v in debt],
        'cash': [B(v) for v in cash],
        'net_debt': [B(d - c) if d is not None and c is not None else None for d, c in zip(debt, cash)],
        'gross_margin': [round(g_ / r * 100, 1) if g_ is not None and r and r > 0 else None
                         for g_, r in zip(gp, rev)],
        'net_margin': [round(x / r * 100, 1) if x is not None and r and r > 0 else None
                       for x, r in zip(ni, rev)],
        'roe': [_pct(v, 1) for v in col('roe')],
        'roic': [_pct(v, 1) for v in col('roic')],
        'net_income': [B(v) for v in ni],
        'eps': [_round(v, 2) for v in col('eps')],
        'ebitda': [B(v) for v in col('ebitda')],
    }


# ════════════════════════════════════════════════════════════════════════════
# Perfil EN VIVO (precio, capitalización, empleados, márgenes TTM…)
# ════════════════════════════════════════════════════════════════════════════

_PROFILE_KEYS = ('available', 'source', 'as_of', 'symbol', 'currency', 'price', 'prev_close',
                 'change_pct', 'price_usd', 'market_cap_usd_b', 'employees', 'sector',
                 'industry', 'country', 'website', 'summary', 'revenue_ttm_usd_b',
                 'gross_margin', 'operating_margin', 'profit_margin', 'revenue_growth',
                 'pe_trailing', 'pe_forward', 'dividend_yield', 'week52_low', 'week52_high',
                 'target_mean', 'recommendation', 'reason',
                 # extras (no rompen el contrato). revenue_growth_q = crecimiento
                 # del ÚLTIMO TRIMESTRE vs el mismo trimestre del año anterior (%)
                 # — distinto de revenue_growth, que es SOLO el TTM interanual.
                 'reason_en', 'name', 'exchange', 'market_state', 'market_time', 'sources',
                 'revenue_growth_q')


def _blank_profile(symbol=None):
    p = {k: None for k in _PROFILE_KEYS}
    p.update({'available': False, 'symbol': symbol, 'as_of': _now_iso(), 'sources': []})
    return p


def _change_pct(price, prev):
    return round((price / prev - 1) * 100, 2) if price is not None and prev else None


def _unix_iso(v):
    ts = _num(v)
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    except (OverflowError, OSError, ValueError):
        return None


def yahoo_quote_summary_to_profile(payload, fx=None, symbol=None):
    """Payload de Yahoo quoteSummary → perfil en vivo (contrato). Márgenes,
    crecimiento y dividendo en %; precio/52 semanas/objetivo en moneda LOCAL;
    price_usd, capitalización e ingresos TTM convertidos a USD. None si el
    payload no trae resultado.

    Crecimiento: Yahoo solo da el del ÚLTIMO TRIMESTRE interanual → sale en
    `revenue_growth_q`; `revenue_growth` (TTM interanual) queda None."""
    res = (((payload or {}).get('quoteSummary') or {}).get('result') or [])
    r0 = res[0] if res and isinstance(res[0], dict) else None
    if not r0:
        return None
    pm = r0.get('price') or {}
    sp = r0.get('summaryProfile') or r0.get('assetProfile') or {}
    fd = r0.get('financialData') or {}
    ks = r0.get('defaultKeyStatistics') or {}
    sd = r0.get('summaryDetail') or {}

    p = _blank_profile(_str(pm.get('symbol')) or symbol)
    cur = _str(pm.get('currency')) or _str(sd.get('currency')) or _str(fd.get('financialCurrency'))
    price = _num(pm.get('regularMarketPrice'))
    prev = (_num(pm.get('regularMarketPreviousClose')) or _num(sd.get('regularMarketPreviousClose'))
            or _num(sd.get('previousClose')))
    chg = _change_pct(price, prev)
    if chg is None and _num(pm.get('regularMarketChangePercent')) is not None:
        chg = round(_num(pm.get('regularMarketChangePercent')) * 100, 2)   # quoteSummary: fracción
    rate_px = _usd_rate(cur, fx)
    # capitalización: Yahoo la da en la moneda MAYOR aunque el precio venga en
    # unidad menor ('GBp' → la capitalización ya está en libras)
    mcap = _num(pm.get('marketCap')) or _num(sd.get('marketCap'))
    rate_mc = _usd_rate(_major(cur), fx)
    fin_cur = _str(fd.get('financialCurrency')) or _major(cur)
    rev = _num(fd.get('totalRevenue'))
    rate_rev = _usd_rate(fin_cur, fx)
    gm = _num(fd.get('grossMargins'))
    if gm == 0 and not _num(fd.get('grossProfits')):
        gm = None     # bancos/aseguradoras: Yahoo pone 0, no es un margen real
    emp = _num(sp.get('fullTimeEmployees'))
    rec = _str(fd.get('recommendationKey'))
    dy = _num(sd.get('dividendYield'))
    if dy is None:
        dy = _num(sd.get('trailingAnnualDividendYield'))

    p.update({
        'source': 'yahoo',
        'sources': ['yahoo'],
        'currency': cur,
        'name': _str(pm.get('longName')) or _str(pm.get('shortName')),
        'exchange': _str(pm.get('exchangeName')),
        'market_state': _str(pm.get('marketState')),
        'market_time': _unix_iso(pm.get('regularMarketTime')),
        'price': _round(price, 4),
        'prev_close': _round(prev, 4),
        'change_pct': chg,
        'price_usd': _round(price * rate_px, 4) if price is not None and rate_px else None,
        'market_cap_usd_b': round(mcap * rate_mc / 1e9, 3) if mcap and rate_mc else None,
        'employees': int(emp) if emp else None,
        'sector': _str(sp.get('sector')),
        'industry': _str(sp.get('industry')),
        'country': _str(sp.get('country')),
        'website': _str(sp.get('website')),
        'summary': _str(sp.get('longBusinessSummary')),
        'revenue_ttm_usd_b': round(rev * rate_rev / 1e9, 3) if rev and rate_rev else None,
        'gross_margin': _pct(gm),
        'operating_margin': _pct(_num(fd.get('operatingMargins'))),
        'profit_margin': _pct(_num(fd.get('profitMargins'))),
        # financialData.revenueGrowth es "Quarterly Revenue Growth (yoy)": el
        # ÚLTIMO TRIMESTRE vs el mismo trimestre del año anterior — NO el
        # crecimiento de los ingresos de 12 meses. Va en su propia clave para
        # que la UI lo rotule honestamente; `revenue_growth` queda SOLO para el
        # crecimiento TTM real (Finnhub revenueGrowthTTMYoy).
        'revenue_growth_q': _pct(_num(fd.get('revenueGrowth'))),
        'pe_trailing': _round(_num(sd.get('trailingPE')), 2),
        'pe_forward': _round(_num(sd.get('forwardPE')) or _num(ks.get('forwardPE')), 2),
        'dividend_yield': _pct(dy),
        'week52_low': _round(_num(sd.get('fiftyTwoWeekLow')), 4),
        'week52_high': _round(_num(sd.get('fiftyTwoWeekHigh')), 4),
        'target_mean': _round(_num(fd.get('targetMeanPrice')), 4),
        'recommendation': rec if rec and rec.lower() != 'none' else None,
    })
    p['available'] = p['price'] is not None or p['market_cap_usd_b'] is not None
    return p


def finnhub_to_profile(profile2, quote, metric=None, fx=None, symbol=None):
    """Finnhub /stock/profile2 + /quote (+ /stock/metric opcional) → perfil.

    Esta ruta SOLO se usa para listados de EE.UU. (_compute_live), así que el
    precio de /quote, el cierre previo y el rango de 52 semanas de /metric
    están en USD. OJO: profile2.currency NO es la moneda de cotización sino la
    de los REPORTES de la empresa ("currency used in company filings"): un ADR
    de TSMC trae 'TWD', de ASML 'EUR'. Rotular el precio con ella mostraría
    "180.50 TWD" y convertiría mal price_usd.

    marketCapitalization viene en MILLONES, en una unidad que Finnhub no
    documenta con claridad para las empresas que reportan en otra moneda:
    solo se usa si la moneda de reporte es USD (sin adivinar: la UI cae a
    otra fuente o muestra "—"). Los márgenes de /stock/metric ya vienen en %."""
    p2 = profile2 if isinstance(profile2, dict) else {}
    qt = quote if isinstance(quote, dict) else {}
    mt = metric if isinstance(metric, dict) else {}
    price = _num(qt.get('c')) or None          # Finnhub responde c=0 si no conoce el símbolo
    prev = _num(qt.get('pc')) or None
    cur = 'USD'                                # listado de EE.UU. → cotiza en USD
    rate = 1.0
    filing_cur = (_str(p2.get('currency')) or 'USD').upper()
    mc = _num(p2.get('marketCapitalization')) if filing_cur == 'USD' else None
    p = _blank_profile(_str(p2.get('ticker')) or symbol)
    chg = _change_pct(price, prev)
    if chg is None and _num(qt.get('dp')) is not None and price is not None:
        chg = round(_num(qt.get('dp')), 2)
    p.update({
        'source': 'finnhub',
        'sources': ['finnhub'],
        'currency': cur,
        'name': _str(p2.get('name')),
        'exchange': _str(p2.get('exchange')),
        'market_time': _unix_iso(qt.get('t')),
        'price': _round(price, 4),
        'prev_close': _round(prev, 4),
        'change_pct': chg,
        'price_usd': _round(price * rate, 4) if price is not None and rate else None,
        'market_cap_usd_b': round(mc * rate / 1000.0, 3) if mc and rate else None,
        'industry': _str(p2.get('finnhubIndustry')),
        'country': _str(p2.get('country')),
        'website': _str(p2.get('weburl')),
        'gross_margin': _round(_num(mt.get('grossMarginTTM')), 2),
        'operating_margin': _round(_num(mt.get('operatingMarginTTM')), 2),
        'profit_margin': _round(_num(mt.get('netProfitMarginTTM')), 2),
        'revenue_growth': _round(_num(mt.get('revenueGrowthTTMYoy')), 2),
        'pe_trailing': _round(_first(mt, 'peTTM', 'peBasicExclExtraTTM'), 2),
        'dividend_yield': _round(_num(mt.get('dividendYieldIndicatedAnnual')), 2),
        'week52_low': _round(_num(mt.get('52WeekLow')), 4),
        'week52_high': _round(_num(mt.get('52WeekHigh')), 4),
    })
    p['available'] = p['price'] is not None or p['market_cap_usd_b'] is not None
    return p


def yahoo_chart_to_profile(payload, fx=None, symbol=None):
    """Último recurso de precio: Yahoo v8/chart (no exige crumb). Solo precio,
    cierre previo y rango de 52 semanas si el meta lo trae."""
    res = (((payload or {}).get('chart') or {}).get('result') or [None])[0]
    if not isinstance(res, dict):
        return None
    meta = res.get('meta') or {}
    cur = _str(meta.get('currency'))
    price = _num(meta.get('regularMarketPrice'))
    ts = res.get('timestamp') or []
    closes = ((res.get('indicators') or {}).get('quote') or [{}])[0].get('close') or []
    pairs = [(t, c) for t, c in zip(ts, closes) if c is not None]
    prev = None
    if pairs:
        # si la última vela es de HOY (misma fecha que regularMarketTime), el
        # cierre previo es la penúltima; si no, la última.
        mt = _num(meta.get('regularMarketTime'))
        last_day = datetime.fromtimestamp(pairs[-1][0], timezone.utc).date() if pairs[-1][0] else None
        mt_day = datetime.fromtimestamp(mt, timezone.utc).date() if mt else None
        if last_day and mt_day and last_day == mt_day:
            prev = pairs[-2][1] if len(pairs) >= 2 else None
        else:
            prev = pairs[-1][1]
    if price is None and pairs:
        price = pairs[-1][1]
    rate = _usd_rate(cur, fx)
    p = _blank_profile(_str(meta.get('symbol')) or symbol)
    p.update({
        'source': 'yahoo',
        'sources': ['yahoo_chart'],
        'currency': cur,
        'name': _str(meta.get('longName')) or _str(meta.get('shortName')),
        'exchange': _str(meta.get('exchangeName')),
        'market_time': _unix_iso(meta.get('regularMarketTime')),
        'price': _round(price, 4),
        'prev_close': _round(prev, 4),
        'change_pct': _change_pct(price, prev),
        'price_usd': _round(price * rate, 4) if price is not None and rate else None,
        'week52_low': _round(_num(meta.get('fiftyTwoWeekLow')), 4),
        'week52_high': _round(_num(meta.get('fiftyTwoWeekHigh')), 4),
    })
    p['available'] = p['price'] is not None
    return p


def _merge_profile(base, extra):
    """Rellena los None de `base` con `extra` (sin pisar lo que ya hay)."""
    if not base:
        return extra
    if not extra:
        return base
    for k, v in extra.items():
        if k in ('source', 'sources', 'as_of', 'reason', 'reason_en'):
            continue
        if base.get(k) is None and v is not None:
            base[k] = v
    base['sources'] = list(base.get('sources') or []) + [s for s in (extra.get('sources') or [])
                                                          if s not in (base.get('sources') or [])]
    base['available'] = base.get('price') is not None or base.get('market_cap_usd_b') is not None
    return base


def _fetch_yahoo_summary(t):
    data, err = _yahoo_get(_Y_QS_URL.format(sym=_sym(t)), {'modules': _Y_QS_MODULES})
    if data is None:
        return None, err or 'sin datos'
    p = yahoo_quote_summary_to_profile(data, symbol=t)
    return (p, None) if p and p.get('available') else (None, 'sin datos')


def _fetch_finnhub_profile(t, key):
    p2, e1 = _get_json(_FH_BASE + 'stock/profile2', {'symbol': t, 'token': key})
    qt, e2 = _get_json(_FH_BASE + 'quote', {'symbol': t, 'token': key})
    mt, _e3 = _get_json(_FH_BASE + 'stock/metric', {'symbol': t, 'metric': 'all', 'token': key})
    metric = mt.get('metric') if isinstance(mt, dict) else None
    p = finnhub_to_profile(p2, qt, metric, symbol=t)
    return (p, None) if p and p.get('available') else (None, e2 or e1 or 'sin datos')


def _fetch_yahoo_chart(t):
    data, err = _get_json(_Y_CHART_URL.format(sym=_sym(t)), {'interval': '1d', 'range': '5d'})
    if data is None:
        return None, err or 'sin datos'
    p = yahoo_chart_to_profile(data, symbol=t)
    return (p, None) if p and p.get('available') else (None, 'sin datos')


def get_live_profile(ticker, finnhub_key=None, use_cache=True):
    """Perfil EN VIVO de una empresa cotizada (cualquier bolsa).

    Yahoo quoteSummary (con crumb) → Finnhub profile2+quote(+metric) si es de
    EE.UU. y hay FINNHUB_KEY → Yahoo chart (solo precio). Caché 90 s. Siempre
    devuelve TODAS las claves del contrato; `available` dice si hay algo.
    `revenue_growth` = crecimiento TTM interanual (solo si la fuente lo da:
    Finnhub); `revenue_growth_q` = último trimestre vs el mismo trimestre del
    año anterior (Yahoo). No son el mismo número: la UI debe rotularlos así."""
    t = (ticker or '').strip().upper()
    if not t:
        p = _blank_profile(None)
        p['reason'], p['reason_en'] = 'ticker vacío', 'empty ticker'
        return p
    if use_cache:
        hit = _cache_get(_LIVE_CACHE, t)
        if hit is not None:
            return hit
    fh = _FINNHUB_DEFAULT if finnhub_key is None else finnhub_key
    with _lock_for('live:' + t):
        if use_cache:
            hit = _cache_get(_LIVE_CACHE, t)
            if hit is not None:
                return hit
        return _compute_live(t, fh)


def _compute_live(t, fh):
    notes_es, notes_en = [], []

    def attempt(src, fn):
        try:
            res, err = fn()
        except Exception as e:  # noqa: BLE001
            log.warning('company_data live %s %s: %s', src, t, type(e).__name__)
            res, err = None, type(e).__name__
        if res is None:
            es, en = _explain(src, err)
            notes_es.append(es)
            notes_en.append(en)
        return res

    prof = attempt('yahoo', lambda: _fetch_yahoo_summary(t))
    if prof is None or prof.get('price') is None:
        if fh and not _q.is_intl(t):
            prof = _merge_profile(prof, attempt('finnhub', lambda: _fetch_finnhub_profile(t, fh)))
        elif not fh and not _q.is_intl(t):
            es, en = _explain('finnhub', 'no_key')
            notes_es.append(es)
            notes_en.append(en)
    if prof is None or prof.get('price') is None:
        prof = _merge_profile(prof, attempt('yahoo_chart', lambda: _fetch_yahoo_chart(t)))

    if prof and prof.get('available'):
        prof['as_of'] = _now_iso()
        prof['symbol'] = prof.get('symbol') or t
        prof['reason'] = prof['reason_en'] = None
        _cache_put(_LIVE_CACHE, t, prof, LIVE_TTL_OK)
        return copy.deepcopy(prof)

    out = _blank_profile(t)
    out['reason'] = f'Sin datos de mercado en vivo para {t} — ' + ' · '.join(notes_es)
    out['reason_en'] = f'No live market data for {t} — ' + ' · '.join(notes_en)
    _cache_put(_LIVE_CACHE, t, out, LIVE_TTL_FAIL)
    return out
