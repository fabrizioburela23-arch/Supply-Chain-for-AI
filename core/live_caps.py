"""core/live_caps.py — capitalización EN VIVO de TODAS las cotizadas del grafo.

Pedido explícito (2026-09-28): "necesito que todo esté en vivo". El catálogo
(NODE_META.mktcap_b) es estático; el mapa, el comparador, la simulación, el
portafolio y la terminal lo leían tal cual. Aquí se consulta en LOTE a Yahoo
(~580 símbolos en ~15 pedidos), en un hilo de fondo, con caché de 15 min.
El cliente (app.html, KhipuLiveCaps) pisa NODE_META con estos valores y
marca cada uno como "en vivo". Sin red → devuelve lo último que tenga (o nada).
"""
import logging
import threading
import time
from datetime import datetime, timezone

log = logging.getLogger(__name__)

TTL_S = 15 * 60
_STATE = {'caps': {}, 'as_of': None, 'ts': 0.0, 'running': False, 'error': None}
_LOCK = threading.Lock()


def _symbols_by_id():
    from core.entities import get_index
    out = {}
    for nid, n in get_index()['nodos'].items():
        mkt = (n.get('mkt') or '').strip().upper()
        if mkt:
            out[nid] = mkt
    return out


def refresh(fetch=None):
    """Consulta todas las cotizadas (bloqueante). `fetch` inyectable en tests."""
    from core.quotes import fetch_quotes_batch_yahoo
    fetch = fetch or fetch_quotes_batch_yahoo
    ids = _symbols_by_id()
    try:
        quotes = fetch(sorted(set(ids.values())))
        caps = {}
        for nid, sym in ids.items():
            q = quotes.get(sym)
            if q and (q.get('mcap_b') is not None or q.get('price') is not None):
                caps[nid] = {'mcap_b': q.get('mcap_b'), 'price': q.get('price'),
                             'currency': q.get('currency'), 'change_pct': q.get('change_pct'),
                             'symbol': sym}
        with _LOCK:
            if caps:     # un fallo total NO borra lo último bueno
                _STATE.update(caps=caps, as_of=datetime.now(timezone.utc).isoformat(), error=None)
            else:
                _STATE['error'] = 'sin datos de la fuente'
            _STATE['ts'] = time.time()
        if caps:
            # Phase 2: movimientos anómalos REALES → investigación automática
            # (apagado por defecto: RESEARCH_AUTO_EVENTS=on)
            try:
                from research.auto_events import dispatch_price_anomalies
                dispatch_price_anomalies(caps)
            except Exception as e:  # noqa: BLE001
                log.warning('live_caps → auto_events: %s', type(e).__name__)
    except Exception as e:  # noqa: BLE001
        log.warning('live_caps: %s', e)
        with _LOCK:
            _STATE.update(error=type(e).__name__, ts=time.time())
    finally:
        with _LOCK:
            _STATE['running'] = False


def get_caps(start=True):
    """Estado actual; si está vencido lanza un refresco en segundo plano."""
    with _LOCK:
        stale = time.time() - _STATE['ts'] > TTL_S
        if start and stale and not _STATE['running']:
            _STATE['running'] = True
            threading.Thread(target=refresh, name='live-caps', daemon=True).start()
        return {'caps': dict(_STATE['caps']), 'as_of': _STATE['as_of'], 'source': 'yahoo',
                'warming': _STATE['running'] and not _STATE['caps'], 'refreshing': _STATE['running'],
                'error': _STATE['error'], 'n': len(_STATE['caps'])}
