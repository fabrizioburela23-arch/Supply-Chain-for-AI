"""core/live_fundamentals.py — FUNDAMENTALES EN VIVO de TODAS las cotizadas del grafo.

Pedido de Fabrizio (2026-10-05): "necesito que sean en vivo siempre los que varían; los
únicos fijos, tipo fundación o productos". Hasta ahora el margen, el crecimiento, los
ingresos y los empleados reales solo se pedían al ABRIR la ficha de una empresa; el resto
de la app (NRS, rankings, comparador, gráficos, simulación, Insights) usaba el número
curado del catálogo.

Aquí, en segundo plano (core/scheduler, cada 5 min), se piden por TANDAS los perfiles en
vivo (core/company_data.get_live_profile: Yahoo quoteSummary → Finnhub) de las ~570
cotizadas: primero las nunca pedidas, luego las más viejas. Cada empresa se refresca al
menos 1×/día (los fundamentales cambian con cada reporte trimestral; el PRECIO y la
capitalización ya van cada 15 min por core/live_caps). El cliente los aplica a todo el
catálogo al cargar (window.KhipuLiveFund) y cada dato lleva fuente y fecha.
"""
import logging
import threading
import time
from datetime import datetime, timezone

log = logging.getLogger(__name__)

BATCH = 40                 # empresas por tanda (≈ 1 tanda cada 5 min → todo el grafo en ~1 h)
MAX_AGE_S = 24 * 3600      # refresco mínimo diario
FIELDS = ('operating_margin', 'profit_margin', 'gross_margin', 'revenue_ttm_usd_b', 'revenue_growth_q',
          'revenue_growth', 'employees', 'pe_trailing', 'pe_forward')
_STATE = {'data': {}, 'running': False, 'last_run': None, 'last_error': None, 'runs': 0}
_LOCK = threading.Lock()


def _universe():
    from core.live_caps import _symbols_by_id
    return _symbols_by_id()


def _pick(ids, now, n=BATCH):
    """Las que faltan primero; luego las más viejas que MAX_AGE_S."""
    with _LOCK:
        data = dict(_STATE['data'])
    missing = [i for i in ids if i not in data]
    old = sorted((i for i in ids if i in data and now - data[i].get('ts', 0) > MAX_AGE_S), key=lambda i: data[i].get('ts', 0))
    return (missing + old)[:n]


def refresh(profile_fn=None, now=None, n=BATCH):
    """Una tanda (bloqueante; el reloj del servidor la llama). Devuelve un resumen."""
    from core.company_data import get_live_profile
    profile_fn = profile_fn or get_live_profile
    now = now or time.time()
    with _LOCK:
        if _STATE['running']:
            return {'skipped': 'running'}
        _STATE['running'] = True
    ok = fail = 0
    try:
        ids = _universe()
        for nid in _pick(list(ids), now, n):
            sym = ids[nid]
            try:
                p = profile_fn(sym) or {}
            except Exception as e:  # noqa: BLE001
                p = {'available': False, 'reason': type(e).__name__}
            rec = {k: p.get(k) for k in FIELDS if p.get(k) is not None}
            if p.get('available') and rec:
                rec.update(symbol=sym, source=(p.get('source') or 'yahoo'), as_of=p.get('as_of') or
                           datetime.now(timezone.utc).isoformat(), ts=now)
                ok += 1
            else:
                # sin dato: se recuerda el intento (para no reintentar en cada tanda) sin pisar lo último bueno
                with _LOCK:
                    prev = _STATE['data'].get(nid)
                rec = dict(prev or {}, symbol=sym, ts=now, missing=not prev)
                fail += 1
            with _LOCK:
                _STATE['data'][nid] = rec
        with _LOCK:
            _STATE.update(last_run=datetime.now(timezone.utc).isoformat(), last_error=None, runs=_STATE['runs'] + 1)
        return {'ok': ok, 'no_data': fail, 'have': len([1 for v in _STATE['data'].values() if not v.get('missing')]),
                'universe': len(ids)}
    except Exception as e:  # noqa: BLE001
        log.warning('live_fundamentals: %s', e)
        with _LOCK:
            _STATE['last_error'] = f'{type(e).__name__}: {str(e)[:120]}'
        return {'error': _STATE['last_error']}
    finally:
        with _LOCK:
            _STATE['running'] = False


def get_all():
    """{fund: {node_id: {operating_margin, revenue_growth_q, …, source, as_of}}, n, universe, last_run}."""
    with _LOCK:
        data = {k: {f: v for f, v in r.items() if f != 'ts'} for k, r in _STATE['data'].items() if not r.get('missing')}
        return {'fund': data, 'n': len(data), 'last_run': _STATE['last_run'], 'error': _STATE['last_error'],
                'note_es': 'Fundamentales reales (últimos 12 meses / último trimestre) de las cotizadas; se refrescan a diario.',
                'note_en': 'Real fundamentals (last 12 months / last quarter) of listed companies; refreshed daily.'}


def live_margin(nid):
    """Margen operativo REAL (fracción) de una empresa, o None si aún no hay dato en vivo."""
    with _LOCK:
        r = _STATE['data'].get(nid) or {}
    v = r.get('operating_margin')
    try:
        return None if v is None or r.get('missing') else float(v) / 100.0
    except (TypeError, ValueError):
        return None
