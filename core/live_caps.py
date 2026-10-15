"""core/live_caps.py — capitalización EN VIVO de TODAS las cotizadas del grafo.

Pedido explícito (2026-09-28): "necesito que todo esté en vivo". El catálogo
(NODE_META.mktcap_b) es estático; el mapa, el comparador, la simulación, el
portafolio y la terminal lo leían tal cual. Aquí se consulta en LOTE a Yahoo
(~580 símbolos en ~15 pedidos), en un hilo de fondo, con caché de 15 min.
El cliente (app.html, KhipuLiveCaps) pisa NODE_META con estos valores y
marca cada uno como "en vivo". Sin red → devuelve lo último que tenga (o nada).

Lote L (2026-10-15): el universo es `core.instruments.live_symbols()` — el grafo VIGENTE (catálogo + empresas
importadas a Postgres con su listado principal), un símbolo una sola vez, sin listados dados de baja. Los símbolos
NUEVOS (fuera del catálogo del repo) entran de a `NEW_PER_CYCLE` por ciclo (`instruments.phase_in`) y los pedidos a
Yahoo pasan por el tope de 15 por minuto (core/quotes.YAHOO_BATCH_LIMITER): importar miles de empresas alarga el
ciclo, nunca sube la tasa. La capitalización sale SIEMPRE de Yahoo en vivo (nunca de la ficha).
"""
import logging
import math
import threading
import time
from datetime import datetime, timezone

log = logging.getLogger(__name__)

TTL_S = 15 * 60
NEW_PER_CYCLE = 120          # símbolos nuevos (fuera del catálogo del repo) que se suman por ciclo = 3 pedidos de 40
_STATE = {'caps': {}, 'as_of': None, 'ts': 0.0, 'running': False, 'error': None, 'cycle': None}
_LOCK = threading.Lock()
_PHASE = {'admitted': set(), 'universe': 0, 'pending': 0}


def _symbols_by_id():
    """{company_id: símbolo de Yahoo} = EL universo en vivo (core.instruments.live_symbols): primarios vigentes del
    grafo, uno por símbolo, en orden de prioridad (catálogo → base → importados). Lo leen también los fundamentales
    en vivo (core/live_fundamentals)."""
    from core import instruments
    return instruments.live_symbols()


def _phase(ids):
    """(ids de este ciclo, símbolos nuevos admitidos ahora, pendientes). El catálogo entra siempre; lo nuevo de a
    NEW_PER_CYCLE (lo ya admitido en este proceso sigue entrando)."""
    from core import instruments
    syms = list(dict.fromkeys(ids.values()))
    inc, now, pending = instruments.phase_in(syms, _PHASE['admitted'], NEW_PER_CYCLE)
    _PHASE['admitted'].update(now)
    _PHASE.update(universe=len(syms), pending=len(pending))
    keep = set(inc)
    return {nid: s for nid, s in ids.items() if s in keep}, now, pending


def phase_state():
    """Cuántos símbolos tiene el universo, cuántos nuevos ya entraron y cuántos esperan su tanda."""
    return {'universe': _PHASE['universe'], 'admitted_new': len(_PHASE['admitted']), 'pending': _PHASE['pending'],
            'new_per_cycle': NEW_PER_CYCLE}


def _caps_of(ids, quotes):
    """{company_id: capitalización/precio} de los símbolos que trajeron dato (nunca de la ficha)."""
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
    return caps


def refresh(fetch=None):
    """Consulta todas las cotizadas (bloqueante). `fetch` inyectable en tests."""
    from core.quotes import YAHOO_BATCH_CHUNK, fetch_quotes_batch_yahoo
    fetch = fetch or fetch_quotes_batch_yahoo
    t0 = time.monotonic()
    try:
        ids = _symbols_by_id()     # dentro del try: si falla, el finally libera 'running'
        ids, admitted_now, pending = _phase(ids)
        # el CATÁLOGO primero: tras un despliegue (estado vacío) se publica en cuanto llega (≤ 15 pedidos, sin esperar
        # el minuto del tope de Yahoo) y lo importado completa el ciclo después. Revisión del lote L: con 688 símbolos
        # el pedido 16 esperaba ~60 s y el mapa quedaba un minuto sin capitalizaciones en vivo.
        from core import instruments
        base = instruments.baseline_symbols()
        allsyms = set(ids.values())
        first = sorted(x for x in allsyms if x in base)
        rest = sorted(x for x in allsyms if x not in base)
        syms = first + rest
        warming = not _STATE.get('caps')
        if warming and first and rest:
            parts = [first, rest]
        else:
            parts = [syms]
        quotes, requests = {}, 0
        for i, part in enumerate(parts):
            quotes.update(fetch(part) or {})
            requests += math.ceil(len(part) / YAHOO_BATCH_CHUNK) if part else 0
            if i == 0 and len(parts) > 1:
                early = _caps_of(ids, quotes)
                if early:
                    with _LOCK:
                        if not _STATE.get('caps'):
                            _STATE.update(caps=early, as_of=datetime.now(timezone.utc).isoformat(), error=None,
                                          ts=time.time())
        caps = _caps_of(ids, quotes)
        cycle = {'symbols': len(syms), 'requests': requests,
                 'new_admitted': len(admitted_now), 'pending': len(pending), 'with_data': len(caps),
                 'seconds': round(time.monotonic() - t0, 2), 'at': datetime.now(timezone.utc).isoformat()}
        with _LOCK:
            _STATE['cycle'] = cycle
            if caps:     # un fallo total NO borra lo último bueno (un ciclo con datos reemplaza todo: un
                         # valor viejo nunca sale sellado con la hora de este lote)
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
                'error': _STATE['error'], 'n': len(_STATE['caps']),
                # lote L: tamaño del universo, tandas de símbolos nuevos y el último ciclo (símbolos, pedidos, segundos)
                'universe': phase_state(), 'cycle': _STATE.get('cycle')}
