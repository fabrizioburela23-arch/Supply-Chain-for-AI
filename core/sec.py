"""core/sec.py — SEC EDGAR como EVIDENCIA PRIMARIA (Phase 2).

Fuente oficial y gratuita (requiere User-Agent con contacto; SEC_USER_AGENT).
- latest_filings(ticker): últimos reportes (10-K, 10-Q, 8-K, 20-F, 6-K) con
  fecha, tipo y enlace al documento original.
- filing_sections(url): extractos de Risk Factors y MD&A del documento.
Caché en memoria (tickers 24 h, filings 6 h, documentos 24 h). Nunca lanza:
ante cualquier fallo devuelve vacío — la investigación sigue sin esta fuente.
"""
import os
import re
import threading
import time

import requests

SEC_UA = os.getenv('SEC_USER_AGENT', 'Khipu Finance research@khipu.finance')
FORMS = ('10-K', '10-Q', '8-K', '20-F', '6-K', '40-F')
_H = {'User-Agent': SEC_UA, 'Accept-Encoding': 'gzip, deflate'}
_TICKERS = {'map': None, 'ts': 0.0}
_CACHE = {}          # clave → (ts, valor)
_LOCK = threading.Lock()


def _cached(key, ttl, fn):
    with _LOCK:
        e = _CACHE.get(key)
        if e and time.time() - e[0] < ttl:
            return e[1]
    val = fn()
    if val:
        with _LOCK:
            _CACHE[key] = (time.time(), val)
    return val


def resolve_cik(ticker, getter=None):
    get = getter or requests.get
    t = (ticker or '').upper().strip()
    if '.' in t:
        base, suf = t.rsplit('.', 1)
        # sufijo de BOLSA extranjera (BA.L, HEI.DE, 6488.TWO…) → no es emisor SEC
        # (antes se cortaba el sufijo y BA.L quedaba como Boeing). Clase de
        # acción de EE.UU. (BRK.B) → formato SEC BRK-B.
        if len(suf) == 1 and base.isalpha():
            t = f'{base}-{suf}'
        else:
            return None
    if not t:
        return None
    if not _TICKERS['map'] or time.time() - _TICKERS['ts'] > 86400:
        try:
            r = get('https://www.sec.gov/files/company_tickers.json', headers=_H, timeout=12)
            if r.ok:
                _TICKERS['map'] = {str(v.get('ticker', '')).upper(): str(v.get('cik_str', '')).zfill(10)
                                   for v in r.json().values()}
                _TICKERS['ts'] = time.time()
        except Exception:  # noqa: BLE001
            pass
    return (_TICKERS['map'] or {}).get(t)


def latest_filings(ticker, n=6, getter=None):
    """[{form, date, url, description}] más recientes, o []. Solo emisores
    registrados en la SEC (EE.UU. y extranjeros con ADR que reportan 20-F)."""
    get = getter or requests.get

    def load():
        cik = resolve_cik(ticker, getter=get)
        if not cik:
            return []
        try:
            r = get(f'https://data.sec.gov/submissions/CIK{cik}.json', headers=_H, timeout=15)
            if not r.ok:
                return []
            rec = (r.json().get('filings') or {}).get('recent') or {}
        except Exception:  # noqa: BLE001
            return []
        out = []
        for i, form in enumerate(rec.get('form') or []):
            if form not in FORMS:
                continue
            try:
                acc = rec['accessionNumber'][i].replace('-', '')
                doc = rec['primaryDocument'][i]
                out.append({'form': form, 'date': rec['filingDate'][i],
                            'description': (rec.get('primaryDocDescription') or [''] * (i + 1))[i] or form,
                            'items': (rec.get('items') or [''] * (i + 1))[i] or '',
                            'url': f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}'})
            except (IndexError, KeyError, ValueError):
                continue
            if len(out) >= n:
                break
        return out
    return _cached(('filings', (ticker or '').upper()), 6 * 3600, load) or []


def _strip_html(html):
    html = re.sub(r'(?is)<(script|style|table)[^>]*>.*?</\1>', ' ', html or '')
    text = re.sub(r'(?s)<[^>]+>', ' ', html)
    text = re.sub(r'&#160;|&nbsp;|&#xa0;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&#8217;|&rsquo;|&#x2019;|&#X2019;', "'", text)
    text = text.replace('\u2019', "'")
    return re.sub(r'\s+', ' ', text).strip()


def _section(text, starts, length):
    """Encabezado por PRIORIDAD (los específicos "Item 1A." antes que el
    genérico). Dentro de un marcador, la ÚLTIMA aparición con contenido real
    (la primera suele ser el índice). Un marcador genérico no pisa a uno
    específico: si "Item 1A. Risk Factors" calza, no se busca "Risk Factors"
    (que suele ser una referencia cruzada, "see Risk Factors")."""
    low = text.lower()
    for mk in starts:
        best = ''
        for m in re.finditer(re.escape(mk.lower()), low):
            chunk = text[m.start():m.start() + length]
            if len(chunk) > 400:
                best = chunk
        if best:
            return best
    return ''


def filing_sections(url, length=1600, getter=None):
    """{'risk_factors': str, 'mdna': str} (extractos) o {}."""
    get = getter or requests.get

    def load():
        try:
            r = get(url, headers=_H, timeout=20)
            if not r.ok:
                return {}
            text = _strip_html(r.text[:6_000_000])
        except Exception:  # noqa: BLE001
            return {}
        out = {'risk_factors': _section(text, ['Item 1A. Risk Factors', 'Item 1A.Risk Factors',
                                               'ITEM 1A. RISK FACTORS', 'Risk Factors'], length),
               'mdna': _section(text, ["Item 7. Management's Discussion", "Item 2. Management's Discussion",
                                       "Management's Discussion and Analysis"], length)}
        return {k: v for k, v in out.items() if v}
    return _cached(('doc', url), 24 * 3600, load) or {}


def earnings_dates(ticker, getter=None, years=2):
    """Fechas REALES de los reportes trimestrales: 8-K con el ítem 2.02 («Results of Operations») de los últimos
    `years` años → [(date, 'amc'|'bmo'|'')] ordenadas. La hora sale de acceptanceDateTime (hora del Este de EE.UU.):
    ≥ 16:00 → después del cierre (amc); < 9:30 → antes de la apertura (bmo). Respaldo de price_sim cuando Finnhub
    no trae el historial (2026-11-07: NVDA quedaba sin «cómo reaccionó a sus reportes»). [] si no es emisor SEC."""
    import datetime as _dt
    get = getter or requests.get

    def load():
        cik = resolve_cik(ticker, getter=get)
        if not cik:
            return []
        try:
            r = get(f'https://data.sec.gov/submissions/CIK{cik}.json', headers=_H, timeout=15)
            if not r.ok:
                return []
            rec = (r.json().get('filings') or {}).get('recent') or {}
        except Exception:  # noqa: BLE001
            return []
        since = _dt.date.today() - _dt.timedelta(days=int(366 * years))
        out = []
        for i, form in enumerate(rec.get('form') or []):
            try:
                if form != '8-K' or '2.02' not in str((rec.get('items') or [])[i] or ''):
                    continue
                d = _dt.date.fromisoformat(str(rec['filingDate'][i])[:10])
                acc = str((rec.get('acceptanceDateTime') or [''] * (i + 1))[i] or '')
            except (IndexError, KeyError, ValueError):
                continue
            if d < since:
                continue
            hour = ''
            if len(acc) >= 16 and acc[:10] == d.isoformat():
                hh, mm = int(acc[11:13]), int(acc[14:16])
                hour = 'amc' if hh >= 16 else 'bmo' if (hh, mm) < (9, 30) else ''
            out.append((d, hour))
        return sorted(set(out))
    return _cached(('earn8k', (ticker or '').upper()), 12 * 3600, load) or []
