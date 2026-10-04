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
    try:
        ids = _symbols_by_id()     # dentro del try: si falla, el finally libera 'running'
        quotes = fetch(sorted(set(ids.values())))
        caps = {}
        for nid, sym in ids.items():
            q = quotes.get(sym)
            if q and (q.get('mcap_b') is not None or q.get('price') is not None):
                caps[nid] = {'mcap_b': q.get('mcap_b'), 'price': q.get('price'),
                             # price_usd: convertido con tipo de cambio en vivo (el
                             # cliente SOLO pinta con "$" este, nunca `price` local)
                             'price_usd': q.get('price_usd'),
                             'currency': q.get('currency'), 'change_pct': q.get('change_pct'),
                             'price_ts': q.get('ts'), 'market_state': q.get('market_state'),   # R9: hora real
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
                from research.auto_events import dispatch_earnings, dispatch_price_anomalies
                dispatch_price_anomalies(caps)
                dispatch_earnings()          # 1 vez al día como máximo
            except Exception as e:  # noqa: BLE001
                log.warning('live_caps → auto_events: %s', type(e).__name__)
        # Phase 3: calificar predicciones vencidas de los agentes (1×/día; no gasta
        # IA, solo precios). C10: corre AUNQUE el lote de Yahoo venga vacío y el
        # reloj del servidor (core/scheduler) la llama cada hora de todos modos.
        try:
            _daily_outcomes()
        except Exception as e:  # noqa: BLE001
            log.warning('live_caps → outcomes: %s', type(e).__name__)
    except Exception as e:  # noqa: BLE001
        log.warning('live_caps: %s', e)
        with _LOCK:
            _STATE.update(error=type(e).__name__, ts=time.time())
    finally:
        with _LOCK:
            _STATE['running'] = False


_OUT_STATE = {'day': None, 'last': None, 'last_at': None, 'error': None, 'error_at': None, 'runs': 0}
_OUT_LOCK = threading.Lock()


def _daily_outcomes(now=None):
    """Califica las predicciones vencidas UNA vez por día UTC. C10: el día se marca
    SOLO si la evaluación terminó bien (antes se marcaba antes de correr: un
    timeout de la base o de Yahoo dejaba el día 'hecho' sin calificar nada), y
    el estado (última corrida / error) queda visible en /api/research/health."""
    now = now or datetime.now(timezone.utc)
    day = now.date().isoformat()
    if _OUT_STATE['day'] == day:
        return None
    if not _OUT_LOCK.acquire(blocking=False):      # ya hay una corrida en curso
        return None
    try:
        try:
            from ontology.db import ontology_available, session_scope
            from research.outcomes import evaluate_due
        except Exception:  # noqa: BLE001 — Phase 3 aún no instalada
            return None
        if not ontology_available():
            return None
        try:
            with session_scope() as s:
                res = evaluate_due(s, now=now)
        except Exception as e:  # noqa: BLE001 — se reintenta en la próxima pasada (no se marca el día)
            _OUT_STATE.update(error=f'{type(e).__name__}: {str(e)[:160]}', error_at=now.isoformat())
            log.warning('outcomes diarios: %s', type(e).__name__)
            return None
        _OUT_STATE.update(day=day, last=res, last_at=now.isoformat(), error=None, runs=_OUT_STATE['runs'] + 1)
        log.info('outcomes diarios: %s', res)
        return res
    finally:
        _OUT_LOCK.release()


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
