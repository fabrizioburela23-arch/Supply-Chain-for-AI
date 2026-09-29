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
