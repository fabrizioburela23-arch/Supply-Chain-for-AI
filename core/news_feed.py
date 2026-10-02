"""core/news_feed.py — NOTICIAS DE TU CARTERA, con fecha y sin repetir lo viejo.

Pedido (2026-10-02): "que te dé noticias en vivo, relevantes de acuerdo a tu
cartera o a tus posiciones… siempre me da las mismas emergencias (crisis de
gobernanza en Samsung) pero no sé si es noticia vieja; me lo dice desde hace meses".

Reglas:
  · Cada noticia lleva su FECHA real de publicación y su antigüedad; sin fecha
    no se muestra como "nueva".
  · Ventana: los últimos `days` días (por defecto 7). Lo más viejo no entra.
  · Sin duplicados: mismo titular (normalizado) o misma URL = una sola noticia,
    agrupando las empresas a las que toca.
  · Relevancia: peso de la posición en la cartera × frescura (decae a la mitad
    cada 2 días) × fuente (resumen de Finnhub > titular de GDELT).
  · Etiqueta clara: 🆕 hoy · reciente (≤ 3 días) · "de hace N días".
Fuentes: Finnhub company-news (con resumen; EE.UU.) y GDELT (global, titulares).
Caché por empresa 10 min. Nunca lanza: sin fuentes devuelve vacío con el motivo.
"""
import logging
import math
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

log = logging.getLogger('khipu')
_CACHE, _LOCK = {}, threading.Lock()
TTL_S = 600


def _norm_title(t):
    t = re.sub(r'[^a-z0-9áéíóúñü ]', ' ', str(t or '').lower())
    return re.sub(r'\s+', ' ', t).strip()[:120]


def _parse_dt(v):
    if v is None or v == '':
        return None
    if isinstance(v, (int, float)):
        try:
            return datetime.fromtimestamp(v, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    s = str(v)
    try:
        if re.fullmatch(r'\d{8}T\d{6}Z', s):          # GDELT seendate
            return datetime.strptime(s, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
        d = datetime.fromisoformat(s.replace('Z', '+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _company_news(nid, label, symbol, days, getter=None):
    """[{title, url, outlet, published_at, summary, source}] de UNA empresa."""
    key = (nid, days)
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and time.time() - hit[0] < TTL_S:
            return hit[1]
    from core.config import FINNHUB
    from core.http import _safe_get, _safe_ticker
    get = getter or _safe_get
    out = []
    sym = _safe_ticker(symbol or '') if symbol else None
    if sym and '.' not in sym and FINNHUB:
        today = date.today()
        data, err = get(f'https://finnhub.io/api/v1/company-news?symbol={sym}&from='
                        f'{(today - timedelta(days=days)).isoformat()}&to={today.isoformat()}&token={FINNHUB}')
        if not err and isinstance(data, list):
            for a in data[:25]:
                out.append({'title': a.get('headline'), 'url': a.get('url'), 'outlet': a.get('source'),
                            'published_at': _parse_dt(a.get('datetime')), 'summary': (a.get('summary') or '')[:320],
                            'source': 'finnhub'})
    if len(out) < 3 and label:
        q = re.sub(r'[^A-Za-z0-9 ._-]', '', label)[:60]
        if q:
            data, err = get(f'https://api.gdeltproject.org/api/v2/doc/doc?query={quote(chr(34) + q + chr(34))}'
                            f'&mode=artlist&maxrecords=15&format=json&sort=datedesc&timespan={days}d')
            if not err and isinstance(data, dict):
                for a in (data.get('articles') or [])[:15]:
                    out.append({'title': a.get('title'), 'url': a.get('url'), 'outlet': a.get('domain'),
                                'published_at': _parse_dt(a.get('seendate')), 'summary': '', 'source': 'gdelt'})
    with _LOCK:
        _CACHE[key] = (time.time(), out)
    return out


def portfolio_news(holdings, days=7, limit=30, lang='es', fetch=None):
    """holdings: [{entity_id|id, label, symbol, weight_pct?}] → noticias ordenadas por relevancia."""
    es = not str(lang).startswith('en')
    days = max(1, min(int(days or 7), 30))
    now = datetime.now(timezone.utc)
    cut = now - timedelta(days=days)
    hs = [h for h in (holdings or []) if isinstance(h, dict) and (h.get('label') or h.get('symbol'))][:20]
    if not hs:
        return {'items': [], 'days': days, 'note': 'sin posiciones' if es else 'no positions'}
    fetch = fetch or _company_news
    tot_w = sum(float(h.get('weight_pct') or 0) for h in hs) or float(len(hs))

    def one(h):
        try:
            return h, fetch(h.get('entity_id') or h.get('id') or h.get('symbol'), h.get('label') or h.get('symbol'),
                            h.get('symbol'), days)
        except Exception as e:  # noqa: BLE001
            log.info('news_feed %s: %s', h.get('symbol'), type(e).__name__)
            return h, []
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(one, hs))
    merged = {}
    for h, items in res:
        w = (float(h.get('weight_pct') or 0) or (100.0 / len(hs))) / tot_w * 100
        for it in items:
            if not it.get('title') or not it.get('url'):
                continue
            pub = it.get('published_at')
            if pub is None or pub < cut or pub > now + timedelta(hours=2):
                continue                                   # sin fecha o fuera de la ventana: no entra
            k = _norm_title(it['title'])
            age_h = max(0.0, (now - pub).total_seconds() / 3600)
            fresh = 0.5 ** (age_h / 48)                     # vida media 2 días
            score = (0.3 + w / 100) * fresh * (1.25 if it.get('summary') else 1.0)
            m = merged.get(k) or next((x for x in merged.values() if x['url'] == it['url']), None)
            who = h.get('label') or h.get('symbol')
            if m:
                if who not in m['holdings']:
                    m['holdings'].append(who)
                m['score'] += score * 0.5
                if not m['summary'] and it.get('summary'):
                    m['summary'] = it['summary']
                continue
            merged[k] = {'title': it['title'][:220], 'url': it['url'], 'outlet': it.get('outlet'),
                         'summary': it.get('summary') or '', 'published_at': pub.isoformat(),
                         'age_hours': round(age_h, 1), 'holdings': [who], 'score': score, 'source': it.get('source')}
    items = sorted(merged.values(), key=lambda x: -x['score'])[:limit]
    for x in items:
        a = x['age_hours']
        if a < 24:
            x['freshness'], x['label'] = 'new', ('🆕 hoy' if es else '🆕 today')
        elif a < 72:
            x['freshness'], x['label'] = 'recent', (f'hace {math.ceil(a / 24)} días' if es else f'{math.ceil(a / 24)} days ago')
        else:
            x['freshness'], x['label'] = 'older', (f'de hace {math.ceil(a / 24)} días' if es else f'{math.ceil(a / 24)} days old')
        x['score'] = round(x['score'], 4)
    return {'items': items, 'days': days, 'as_of': now.isoformat(),
            'n_new': sum(1 for x in items if x['freshness'] == 'new'),
            'sources': sorted({x['source'] for x in items if x.get('source')}),
            'note': (f'Noticias publicadas en los últimos {days} días sobre tus posiciones, sin repetir.' if es else
                     f'News published in the last {days} days about your holdings, without repeats.')}
