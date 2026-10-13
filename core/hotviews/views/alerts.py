"""AlertIndex (INFRA_OPERATIVA §4.2 — disparador, no vista; paso 14): (métrica, entidad) → alertas, con los valores
leídos UNA vez por lote de las vistas rápidas en vez de una consulta (NRS) o una llamada a Finnhub (precio) por
alerta.

  · NRS   → `nrs_override` del objeto si existe (manda, como antes) → la tarjeta V3 de la generación vigente (LA
            fórmula, grado de flujo en pares distintos) → respaldo: el cálculo directo de ontology.agents;
  · price → la cotización con sello V4 (core/hotviews/views/quote.py) de TODOS los tickers del lote en una sola
            llamada (caché de 15 s), con la MISMA condición de hoy: sin FINNHUB_KEY no hay precio (no cambia
            el comportamiento de las alertas existentes).

`values(session, rules)` arma el lote; `ontology.agents.evaluate_alert(session, rule, values=…)` lo usa. Lo que se
evalúa queda marcado con la versión de las vistas de las que salió (`versions`).
"""
import time

_STATS = {'batches': 0, 'rules': 0, 'nrs_from_card': 0, 'nrs_fallback': 0, 'prices': 0, 'last_ms': None}


def index(rules):
    """{(métrica, entidad): [posición de la regla]} — qué alertas mira cada valor."""
    out = {}
    for i, r in enumerate(rules or []):
        r = r or {}
        m = r.get('metric')
        key = (m, r.get('entity') if m in ('price', 'nrs') else (r.get('region') or '').lower())
        out.setdefault(key, []).append(i)
    return out


def values(session, rules):
    """{(métrica, entidad): (valor, detalle)} para price y nrs, en lote. Nunca lanza."""
    from ontology.models import ObjectRecord
    t0 = time.perf_counter()
    idx = index(rules)
    ents = sorted({k[1] for k in idx if k[0] in ('price', 'nrs') and k[1]})
    objs = {}
    if ents:
        try:
            for o in session.query(ObjectRecord).filter(ObjectRecord.id.in_(ents)).all():
                objs[o.id] = o
        except Exception:  # noqa: BLE001
            objs = {}
    out, versions = {}, {}
    nrs_ents = [e for (m, e) in idx if m == 'nrs' and e]
    if nrs_ents:
        card_nrs, gen = {}, None
        try:
            from core.hotviews.views import card
            cv = card.db_view()
            if cv is not None:
                allv = cv.nrs_all()
                card_nrs = {e: allv[e]['total'] for e in nrs_ents if e in allv}
                gen = cv.generation
                versions['card'] = {'generation': gen, 'fund_version': cv.nrs_version()}
        except Exception:  # noqa: BLE001
            card_nrs = {}
        for e in nrs_ents:
            o = objs.get(e)
            if o is None:
                out[('nrs', e)] = (None, 'objeto no encontrado')
                continue
            score = (o.properties or {}).get('nrs_override')
            if score is None:
                score = card_nrs.get(e)
                if score is not None:
                    _STATS['nrs_from_card'] += 1
                else:
                    from ontology.agents import _compute_server_nrs
                    score = _compute_server_nrs(session, o)
                    _STATS['nrs_fallback'] += 1
            out[('nrs', e)] = (score, f'NRS({o.label}) = {score}')
    px_ents = [e for (m, e) in idx if m == 'price' and e]
    if px_ents:
        tick = {}
        for e in px_ents:
            o = objs.get(e)
            tick[e] = ((o.properties or {}).get('mkt') if o is not None else None) or e
        stamped = {}
        try:
            from core.config import FINNHUB
            if FINNHUB:
                from core.hotviews.views import quote
                stamped = quote.stamped(sorted(set(tick.values())))
        except Exception:  # noqa: BLE001
            stamped = {}
        for e, t in tick.items():
            q = stamped.get(str(t).upper()) or stamped.get(t)
            if q is None:
                out[('price', e)] = (None, 'sin precio en vivo disponible')
                continue
            _STATS['prices'] += 1
            out[('price', e)] = (q['px'], f"{t} = {q['px']} ({q['stamp'].get('src')}, {q['stamp'].get('as_of')})")
        versions['quotes'] = {'n': len(stamped)}
    _STATS['batches'] += 1
    _STATS['rules'] += len(rules or [])
    _STATS['last_ms'] = round((time.perf_counter() - t0) * 1000, 2)
    out['_versions'] = versions
    return out


def stats():
    return dict(_STATS)
