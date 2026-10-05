"""core/live_facts.py — DATOS EN VIVO para toda llamada de IA.

Complemento del guardián de cifras (core/numbers.py): el guardián impide que
la IA use cifras de MEMORIA; esto le da la cifra CORRECTA. Detecta las
empresas del grafo mencionadas en el prompt (ticker o nombre) y agrega un
bloque "DATOS EN VIVO" con capitalización y precio del momento (perfil en
vivo, con respaldo de Yahoo) o, si es privada, su última valuación VERIFICADA
con fecha (capa private_valuations). Acotado: máx. 4 empresas, 6 s en total,
nunca rompe la llamada de IA (ante cualquier fallo devuelve '').
"""
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timezone

log = logging.getLogger(__name__)

MAX_ENTITIES = 6
# tickers que también son palabras o siglas comunes: "AI" (C3.ai) hacía que TODO texto sobre IA trajera los
# datos de C3.ai (visto en la simulación del IPO de OpenAI, 2026-10-05). Solo cuentan por su NOMBRE.
_AMBIGUOUS_TICKERS = {'AI', 'IT', 'ON', 'ALL', 'NOW', 'ONE', 'ARE', 'CAN', 'GO', 'SO', 'BIG', 'LOW', 'KEY', 'ANY', 'DO',
                      'SEE', 'RUN', 'EV', 'US', 'UK', 'EU', 'CEO', 'CFO', 'IPO', 'ETF', 'GDP', 'USD', 'HBM', 'GPU', 'CPU',
                      'TPU', 'PPA', 'LLM', 'API', 'IOT', 'OPEN', 'LIFE', 'REAL', 'PLAY', 'CASH', 'BEST', 'FAST', 'NEXT',
                      'SAFE', 'TRUE', 'WELL', 'HOLD', 'GOOD', 'PEAK', 'CARE', 'CORE', 'EDGE', 'DATA', 'GRID', 'NET'}
TIMEOUT_S = 6.0
_rx_cache = {'rx': None}
_rx_lock = threading.Lock()
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix='livefacts')


def _label_regex(idx):
    with _rx_lock:
        if _rx_cache['rx'] is None:
            by_label = {}
            for nid, n in idx['nodos'].items():
                lab = (n.get('label') or '').strip()
                if not lab:
                    continue
                by_label.setdefault(lab, nid)
                # "Microsoft (Azure)", "Alphabet (Google Cloud)": también cuenta el nombre sin el paréntesis
                base = re.split(r'\s*\(', lab)[0].strip()
                if base and base != lab and len(base) >= 4:
                    by_label.setdefault(base, nid)
            labels = sorted((x for x in by_label if len(x) >= 4), key=len, reverse=True)
            _rx_cache['rx'] = re.compile(r'(?<![\w])(' + '|'.join(re.escape(x) for x in labels) + r')(?![\w])')
            _rx_cache['by_label'] = by_label
        return _rx_cache['rx'], _rx_cache['by_label']


def detect_entities(text, limit=MAX_ENTITIES):
    """Ids del grafo mencionados en `text`, en orden de aparición."""
    from core.entities import get_index
    if not text:
        return []
    idx = get_index()
    hits = []   # (pos, id)
    rx, by_label = _label_regex(idx)
    for m in rx.finditer(text):
        nid = by_label.get(m.group(1))
        if nid:
            hits.append((m.start(), nid))
    for m in re.finditer(r'(?<![\w.$])([A-Z]{2,5}(?:\.[A-Z]{1,2})?)(?![\w])', text):
        if m.group(1) in _AMBIGUOUS_TICKERS:
            continue
        nid = idx['por_ticker'].get(m.group(1))
        if nid:
            hits.append((m.start(), nid))
    out = []
    for _pos, nid in sorted(hits):
        if nid not in out:
            out.append(nid)
        if len(out) >= limit:
            break
    return out


def _fact_for(nid):
    from core.entities import get_index
    idx = get_index()
    n = idx['nodos'].get(nid) or {}
    label = n.get('label') or nid
    mkt = (n.get('mkt') or '').strip().upper()
    if mkt:
        from core.company_data import get_live_profile
        p = get_live_profile(mkt) or {}
        mc = p.get('market_cap_usd_b') if p.get('available') else None
        price = p.get('price') if p.get('available') else None
        if mc is None:
            try:
                from core.quotes import fetch_market_cap_yahoo
                mc = fetch_market_cap_yahoo(mkt)
            except Exception:  # noqa: BLE001
                mc = None
        if mc is None and price is None:
            return None
        parts = []
        if mc is not None:
            parts.append(f'capitalización de mercado {mc} mil millones USD')
        if price is not None:
            parts.append(f'precio {price} {p.get("currency") or ""}'.strip())
        return f'- {label} ({mkt}, cotiza): ' + '; '.join(parts) + f' [en vivo, {p.get("source") or "yahoo"}]'
    pre = (idx.get('preipo_intel') or {}).get(nid) or {}
    val = pre.get('valuation')
    if not val:
        t = n.get('ticker') or ''
        m = re.search(r'~?\$[\d.,]+\s?[BT]', t)
        val = m.group(0) if m else None
    if val:
        return (f'- {label} (privada, NO cotiza): última valuación VERIFICADA {val} '
                '— no es un precio en vivo; puede haber cambiado')
    return None


def live_facts_block(text):
    """Bloque de texto para anexar al prompt, o '' si no aplica/falla."""
    try:
        ids = detect_entities(text)
        if not ids:
            return ''
        futs = {_POOL.submit(_fact_for, nid): nid for nid in ids}
        done, _ = wait(futs, timeout=TIMEOUT_S)
        lines = []
        for nid in ids:   # conserva el orden de aparición
            f = next((x for x in done if futs[x] == nid), None)
            if f is None:
                continue
            try:
                line = f.result()
            except Exception:  # noqa: BLE001
                line = None
            if line:
                lines.append(line)
        if not lines:
            return ''
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        return ('\n\nDATOS EN VIVO (consultados ahora, ' + now + ') — tienen PRIORIDAD sobre cualquier otra '
                'cifra de este mensaje o de tu memoria:\n' + '\n'.join(lines))
    except Exception as e:  # noqa: BLE001
        log.warning('live_facts: %s', type(e).__name__)
        return ''
