"""research/auto_events.py — eventos AUTOMÁTICOS del mercado real (Phase 2).

PRICE_ANOMALY: tras cada refresco de capitalizaciones en vivo
(core/live_caps), las empresas con un movimiento diario anómalo
(|cambio| ≥ RESEARCH_ANOMALY_PCT, default 8 %) disparan una investigación
QUICK de los agentes suscritos (técnico, noticias, riesgo) SOLO sobre esa
empresa. Límites: máx. RESEARCH_ANOMALY_MAX (default 3) por refresco, el
dedupe de 24 h del router (misma empresa + dirección + día), el tope diario
de gasto del runner. APAGADO por defecto: RESEARCH_AUTO_EVENTS=on lo activa
(el mismo interruptor que las noticias).
Solo eventos REALES: los "what-if" (disparar un factor) NO investigan.
"""
import logging
import os
from datetime import datetime, timezone

log = logging.getLogger(__name__)


def auto_on():
    return os.getenv('RESEARCH_AUTO_EVENTS', 'off').lower() == 'on'


def price_anomalies(caps, threshold=None, limit=None):
    """[(id, change_pct)] con |cambio| ≥ umbral, mayor movimiento primero."""
    thr = float(threshold if threshold is not None else os.getenv('RESEARCH_ANOMALY_PCT', 8))
    lim = int(limit if limit is not None else os.getenv('RESEARCH_ANOMALY_MAX', 3))
    out, seen_sym = [], set()
    for nid, c in sorted((caps or {}).items()):
        try:
            chg = float(c.get('change_pct'))
        except (TypeError, ValueError):
            continue
        sym = c.get('symbol') or nid
        if abs(chg) >= thr and sym not in seen_sym:   # ids duplicados del mismo ticker → 1 sola
            seen_sym.add(sym)
            out.append((nid, round(chg, 2)))
    out.sort(key=lambda x: -abs(x[1]))
    return out[:lim]


def dispatch_price_anomalies(caps, execute=True, session_factory=None, today=None):
    """Crea (y ejecuta) investigaciones por movimientos anómalos. Devuelve la
    lista de resultados del router. Nunca lanza."""
    if not auto_on():
        return []
    try:
        from core.ai import _ai_configured
        from ontology.db import ontology_available, session_scope
        if not (ontology_available() and _ai_configured()):
            return []
        from research.router import dispatch_event
        day = today or datetime.now(timezone.utc).date().isoformat()
        results = []
        for nid, chg in price_anomalies(caps):
            direction = 'sube' if chg > 0 else 'cae'
            ev = {'type': 'PRICE_ANOMALY', 'entities': [nid], 'depth': 'QUICK',
                  # titular ESTABLE en el día → el dedupe de 24 h evita repetir
                  'headline': f'Movimiento anómalo: {nid} {direction} con fuerza el {day}',
                  'change_pct': chg}
            with (session_factory or session_scope)() as s:
                results.append(dispatch_event(s, ev, actor='event:price-anomaly', execute=execute,
                                              limits={'max_depth': 0, 'max_jobs': 1}))
        return results
    except Exception as e:  # noqa: BLE001 — nunca tumba el refresco de precios
        log.warning('auto_events price: %s', e)
        return []


# ── EARNINGS: resultados trimestrales REALES (Finnhub, calendario) ────────────
_EARN_STATE = {'day': None}


def fetch_reported_earnings(day_from, day_to, getter=None):
    """[{symbol, date, epsActual, epsEstimate, revenueActual, …}] ya REPORTADOS
    (epsActual presente) en el rango. Sin FINNHUB_KEY → []."""
    from core.config import FINNHUB
    if not FINNHUB and getter is None:
        return []
    if getter is None:
        from core.http import _safe_get as getter
    data, err = getter(f'https://finnhub.io/api/v1/calendar/earnings?from={day_from}&to={day_to}&token={FINNHUB}')
    rows = (data or {}).get('earningsCalendar') if isinstance(data, dict) else None
    return [r for r in (rows or []) if r.get('symbol') and r.get('epsActual') is not None]


def dispatch_earnings(execute=True, session_factory=None, today=None, getter=None, force=False):
    """UNA vez por día: empresas del grafo que reportaron resultados (ayer/hoy)
    → evento EARNINGS → agentes fundamental/noticias/riesgo, QUICK, solo esa
    empresa, con el BPA/ingresos reales como EVIDENCIA. Máx RESEARCH_EARNINGS_MAX
    (5). Apagado por defecto (RESEARCH_AUTO_EVENTS=on). Nunca lanza."""
    if not auto_on():
        return []
    try:
        from datetime import date, timedelta
        d = today or datetime.now(timezone.utc).date()
        if isinstance(d, str):
            d = date.fromisoformat(d)
        if _EARN_STATE['day'] == d.isoformat() and not force:
            return []
        from core.ai import _ai_configured
        from core.entities import get_index
        from ontology.db import ontology_available, session_scope
        if not (ontology_available() and _ai_configured()):
            return []
        _EARN_STATE['day'] = d.isoformat()
        rows = fetch_reported_earnings((d - timedelta(days=1)).isoformat(), d.isoformat(), getter=getter)
        by_ticker = get_index()['por_ticker']
        from research.router import dispatch_event
        lim = int(os.getenv('RESEARCH_EARNINGS_MAX', 5))
        results, seen = [], set()
        for r in rows:
            nid = by_ticker.get(str(r['symbol']).upper())
            if not nid or nid in seen:
                continue
            seen.add(nid)
            ev = {'type': 'EARNINGS', 'entities': [nid], 'depth': 'QUICK',
                  'headline': f"Resultados trimestrales de {nid} (T{r.get('quarter')} {r.get('year')}, {r.get('date')})",
                  'data': {'earnings': {k: r.get(k) for k in ('symbol', 'date', 'quarter', 'year', 'epsActual',
                                                              'epsEstimate', 'revenueActual', 'revenueEstimate')}}}
            with (session_factory or session_scope)() as s:
                results.append(dispatch_event(s, ev, actor='event:earnings', execute=execute,
                                              limits={'max_depth': 0, 'max_jobs': 1}))
            if len(results) >= lim:
                break
        return results
    except Exception as e:  # noqa: BLE001
        log.warning('auto_events earnings: %s', e)
        return []
