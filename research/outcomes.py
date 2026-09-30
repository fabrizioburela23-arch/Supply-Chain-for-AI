"""research/outcomes.py — PHASE 3 · ¿ACERTARON LOS AGENTES? (aprendizaje)

Phase 2 produce claims con postura, horizonte y confianza calculada. Phase 3
las CALIFICA contra lo que de verdad pasó con el precio — sin IA, solo
precios reales — y con eso mide qué tan confiable es cada agente.

1. FOTO DE PARTIDA (record_baseline) — al persistir una claim (runner.py) se
   guarda: entidad, ticker si cotiza, fecha de mercado (Nueva York), precio en
   vivo y SPY en vivo (auditoría), horizonte y checkpoints de evaluación:
       INTRADAY 1 día · SHORT_TERM 7 (intermedio) y 30 · MEDIUM_TERM 30/90 y 180
       LONG_TERM 90/180 y 365 · STRUCTURAL no se califica (n/a).
   Claims anteriores a Phase 3 se completan en la primera evaluación (backfill).

2. EVALUACIÓN (evaluate_due) — cuando vence un checkpoint:
       retorno del activo y de SPY entre el cierre del día de la predicción y el
       primer cierre en/después del vencimiento (serie de cierres AJUSTADOS:
       ambos precios de la MISMA serie → un split no produce un falso −90 %);
       exceso = retorno − retorno SPY; banda (default ±2 %, RESEARCH_OUTCOME_BAND)
       positiva → acierto si exceso > +banda · negativa → si exceso < −banda
       neutral → si |exceso| ≤ banda · mixta / no cotiza → n/a con motivo.
   Append-only e idempotente (única por claim+checkpoint). Las claims
   superadas también se califican: su predicción se hizo. Por lote se pide a
   cada símbolo la ventana de precios MÁS ANTIGUA que necesite (SPY la comparten
   todas); una serie que no llega a la fecha de partida queda pendiente, no n/a.
   Antes de las 16:30 de Nueva York la barra de HOY se descarta (precio en curso).
   Motivo en es/en (reason, reason_en); fuera de EE.UU. = moneda local.
   Limitación conocida: una claim creada DURANTE la sesión usa el cierre de ese
   mismo día como base (unas horas de ventaja); se documenta en PHASE3.md.

3. HISTORIAL Y CALIBRACIÓN (track_record / calibrated_confidence) — sobre los
   checkpoints FINALES: tasa de acierto, Brier de la confianza declarada,
   curva de fiabilidad por tramos (0-0.2 … 0.8-1.0) y confianza calibrada con
   encogimiento bayesiano:  calibrada = (aciertos_tramo + k·cruda)/(n_tramo + k),
   k = 10 (RESEARCH_CALIBRATION_K). Con poca historia → ≈ la cruda.
   Los intermedios se reportan aparte como "señal temprana".
"""
import bisect
import logging
import os
import re
import threading
import time
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from research.models import CalibrationSnapshot, ClaimBaseline, ClaimOutcome, ResearchClaim

log = logging.getLogger('khipu')

METHOD = 'outcome-v1'
CAL_METHOD = 'cal-v1'
BENCH = 'SPY'
# horizonte → [(días, final?)]
CHECKPOINTS = {
    'INTRADAY': [(1, True)],
    'SHORT_TERM': [(7, False), (30, True)],
    'MEDIUM_TERM': [(30, False), (90, False), (180, True)],
    'LONG_TERM': [(90, False), (180, False), (365, True)],
    'STRUCTURAL': [],
}
MAX_LAG_DAYS = 10      # el cierre usado no puede estar a más de 10 días de la fecha buscada
GIVE_UP_DAYS = 20      # 20 días después del vencimiento sin precio → n/a (¿deslistada?)
BUCKETS = ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0))
MIN_N = 5              # por debajo: "sin historial suficiente"
PRIOR_RELIABILITY = 0.5


def _now():
    return datetime.now(timezone.utc)


def band_default():
    """Banda de 'movimiento que cuenta' (fracción). Acepta 0.02 o 2 (= 2 %)."""
    try:
        v = float(os.getenv('RESEARCH_OUTCOME_BAND', '0.02'))
    except (TypeError, ValueError):
        v = 0.02
    if v >= 1:
        v = v / 100.0
    return max(0.0, min(v, 0.5))


def k_default():
    try:
        return max(0.0, float(os.getenv('RESEARCH_CALIBRATION_K', '10')))
    except (TypeError, ValueError):
        return 10.0


# ── fechas de mercado (Nueva York) ───────────────────────────────────────────
def _ny_tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo('America/New_York')
    except Exception:  # noqa: BLE001 — imagen sin tzdata
        return None


def market_date(dt=None):
    """Fecha de la sesión de EE.UU. a la que pertenece un instante."""
    dt = dt or _now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return _ny_datetime(dt).date()


def _ny_datetime(dt):
    """Instante en hora de Nueva York (con tzdata; si no, horario de verano de
    EE.UU. aproximado: 2º domingo de marzo → 1er domingo de noviembre)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    tz = _ny_tz()
    if tz is not None:
        return dt.astimezone(tz)
    y = dt.year
    mar = date(y, 3, 8)
    start = mar + timedelta(days=(6 - mar.weekday()) % 7)
    nov = date(y, 11, 1)
    end = nov + timedelta(days=(6 - nov.weekday()) % 7)
    off = -4 if start <= dt.date() < end else -5
    return dt.astimezone(timezone(timedelta(hours=off)))


def build_checkpoints(horizon, anchor):
    out = []
    for days, final in CHECKPOINTS.get(horizon, []):
        out.append({'label': f"{'final' if final else 'interim'}_{days}d", 'days': days,
                    'due_date': (anchor + timedelta(days=days)).isoformat(), 'final': final})
    return out


def symbol_for(entity_id):
    """Ticker cotizado de la entidad (campo mkt del catálogo) o None."""
    from core.entities import get_index
    from core.http import _safe_ticker
    n = get_index()['nodos'].get(entity_id) or {}
    return _safe_ticker(n.get('mkt')) if n.get('mkt') else None


def na_reasons(horizon, stance, symbol):
    """(motivo_es, motivo_en) por el que una claim NO se califica, o (None, None)."""
    if horizon == 'STRUCTURAL':
        return ('horizonte ESTRUCTURAL (más de 5 años): no se califica con el precio',
                'STRUCTURAL horizon (over 5 years): not scored with the price')
    if stance == 'mixed':
        return 'postura mixta: no es falsable con el precio', 'mixed stance: not falsifiable with the price'
    if stance not in ('positive', 'negative', 'neutral'):
        return f'postura desconocida ({stance})', f'unknown stance ({stance})'
    if not symbol:
        return ('no cotiza en bolsa: no hay precio con qué calificarla',
                'not listed: there is no price to score it with')
    return None, None


def na_reason_for(horizon, stance, symbol):
    return na_reasons(horizon, stance, symbol)[0]


_US_RX = re.compile(r'^[A-Z]{1,5}(?:[.\-][A-C])?$')


def is_us_listing(symbol):
    """¿Ticker de EE.UU. (NVDA, BRK.B, MOG-A)? Los de otras bolsas llevan sufijo
    de Yahoo (2330.TW, 9984.T, BA.L…) o empiezan con dígito: cotizan en moneda local."""
    return bool(symbol) and bool(_US_RX.match(str(symbol).upper()))


# ── precios en vivo al crear la claim (solo auditoría) ───────────────────────
def live_quotes(symbols, profile_fn=None, timeout=6.0):
    """{símbolo: {price, currency, source, as_of}} con el perfil en vivo.
    Acotado en tiempo (nunca frena la investigación más de `timeout` s)."""
    from concurrent.futures import ThreadPoolExecutor, wait
    syms = [s for s in dict.fromkeys(symbols or []) if s]
    if not syms:
        return {}
    if profile_fn is None:
        from research.context import DEFAULT_FETCHERS
        profile_fn = DEFAULT_FETCHERS['profile']

    def one(s):
        try:
            p = profile_fn(s) or {}
        except Exception:  # noqa: BLE001
            return None
        if p.get('available') and p.get('price') is not None:
            try:
                return {'price': float(p['price']), 'currency': p.get('currency'),
                        'source': str(p.get('source') or 'live')[:30], 'as_of': p.get('as_of')}
            except (TypeError, ValueError):
                return None
        return None
    out = {}
    ex = ThreadPoolExecutor(max_workers=min(4, len(syms)))
    try:
        futs = {ex.submit(one, s): s for s in syms}
        done, _ = wait(futs, timeout=timeout)
        for f in done:
            try:
                r = f.result()
            except Exception:  # noqa: BLE001
                r = None
            if r:
                out[futs[f]] = r
    finally:
        ex.shutdown(wait=False)
    return out


def record_baseline(session, claim, quotes=None, band=None, calibrated=None, source=None):
    """Crea (una sola vez) la foto de partida de una claim. Devuelve la fila."""
    prev = session.query(ClaimBaseline).filter(ClaimBaseline.claim_id == claim.id).first()
    if prev:
        return prev
    sym = symbol_for(claim.subject_entity_id)
    created = claim.created_at or claim.valid_from or _now()
    anchor = market_date(created)
    na = na_reasons(claim.horizon, claim.stance, sym)[0]
    q = (quotes or {}).get(sym) or {} if sym else {}
    bq = (quotes or {}).get(BENCH) or {}
    if calibrated is None:
        cal = ((claim.confidence_components or {}).get('calibration') or {})
        calibrated = cal.get('calibrated')
    row = ClaimBaseline(
        claim_id=claim.id, entity_id=claim.subject_entity_id, agent_type=claim.agent_type,
        stance=claim.stance, horizon=claim.horizon, confidence=float(claim.confidence or 0),
        calibrated_confidence=calibrated, symbol=sym, scoreable=na is None, na_reason=na,
        baseline_date=anchor.isoformat(), baseline_price=q.get('price'),
        baseline_currency=q.get('currency'),
        baseline_source=source or (('live:' + q['source']) if q.get('price') is not None else 'sin precio en vivo'),
        benchmark_symbol=BENCH, benchmark_price=bq.get('price'),
        band=band_default() if band is None else band,
        checkpoints=build_checkpoints(claim.horizon, anchor), claim_created_at=created)
    session.add(row)
    session.flush()
    return row


def ensure_baselines(session, limit=2000):
    """Backfill: claims SIN foto de partida (p. ej. anteriores a Phase 3)."""
    rows = (session.query(ResearchClaim)
            .outerjoin(ClaimBaseline, ClaimBaseline.claim_id == ResearchClaim.id)
            .filter(ClaimBaseline.id.is_(None))
            .order_by(ResearchClaim.created_at).limit(limit).all())
    n = 0
    for c in rows:
        try:
            with session.begin_nested():
                record_baseline(session, c, quotes=None, source='backfill (sin precio en vivo)')
            n += 1
        except IntegrityError:
            continue
    return n


# ── búsqueda en series de cierres ────────────────────────────────────────────
def _sorted_keys(series):
    return sorted(series)


def last_on_or_before(series, keys, d, max_lag=MAX_LAG_DAYS):
    i = bisect.bisect_right(keys, d.isoformat()) - 1
    if i < 0:
        return None
    k = keys[i]
    if (d - date.fromisoformat(k)).days > max_lag:
        return None
    return k, float(series[k])


def first_on_or_after(series, keys, d, max_lag=MAX_LAG_DAYS):
    """(fecha, precio) · 'gap' si el primer cierre está demasiado lejos · None si aún no existe."""
    i = bisect.bisect_left(keys, d.isoformat())
    if i >= len(keys):
        return None
    k = keys[i]
    if (date.fromisoformat(k) - d).days > max_lag:
        return 'gap'
    return k, float(series[k])


def default_price_fn(symbol, since):
    """Cierres diarios AJUSTADOS reales (Yahoo) que cubren desde `since`."""
    from core.risk_report import fetch_history
    days = (date.today() - since).days
    rng = '1y' if days <= 350 else ('2y' if days <= 715 else '5y')
    hist, _cur = fetch_history(symbol, rng)
    return hist or None


def judge(stance, excess, band):
    if stance == 'positive':
        return 'hit' if excess > band else 'miss'
    if stance == 'negative':
        return 'hit' if excess < -band else 'miss'
    if stance == 'neutral':
        return 'hit' if abs(excess) <= band else 'miss'
    return 'n/a'


_STANCE_ES = {'positive': 'positiva', 'negative': 'negativa', 'neutral': 'neutral', 'mixed': 'mixta'}


def _na(reason_es, reason_en):
    return {'result': 'n/a', 'reason': reason_es, 'reason_en': reason_en, 'price_source': None}


def score_checkpoint(b, cp, get_series, today):
    """Devuelve dict con el resultado, o None si todavía no se puede calificar."""
    due = date.fromisoformat(cp['due_date'])
    late = (today - due).days
    if not b.scoreable:
        es, en = na_reasons(getattr(b, 'horizon', None), b.stance, b.symbol)
        return _na(b.na_reason or es or 'no calificable', en or 'not scoreable')
    anchor = date.fromisoformat(b.baseline_date)
    s = get_series(b.symbol, anchor - timedelta(days=15))
    bs = get_series(b.benchmark_symbol or BENCH, anchor - timedelta(days=15))
    if not s or not bs:
        if late > GIVE_UP_DAYS:
            return _na('sin serie de precios del proveedor tras %d días' % late,
                       'no price series from the provider after %d days' % late)
        return None
    ks, kb = _sorted_keys(s), _sorted_keys(bs)
    p0, b0 = last_on_or_before(s, ks, anchor), last_on_or_before(bs, kb, anchor)
    p1, b1 = first_on_or_after(s, ks, due), first_on_or_after(bs, kb, due)
    if p1 is None or b1 is None:
        if late > GIVE_UP_DAYS:
            return _na('no hay cierre después del vencimiento (¿suspendida o deslistada?)',
                       'no close after the due date (suspended or delisted?)')
        return None
    if p1 == 'gap' or b1 == 'gap':
        return _na('hueco en la serie de precios alrededor del vencimiento',
                   'gap in the price series around the due date')
    if p0 is None or b0 is None:
        # ¿la serie NO llega hasta la fecha de partida (ventana corta del proveedor)?
        # → reintentar más tarde con una ventana más larga, no es un n/a definitivo
        short = (ks and ks[0] > anchor.isoformat()) or (kb and kb[0] > anchor.isoformat())
        if short and late <= GIVE_UP_DAYS:
            return None
        return _na('sin precio de partida en la serie histórica', 'no starting price in the historical series')
    if p1[0] <= p0[0]:
        return None
    r = p1[1] / p0[1] - 1.0
    rb = b1[1] / b0[1] - 1.0
    ex = r - rb
    res = judge(b.stance, ex, b.band)
    verdict = {'hit': 'acierto', 'miss': 'fallo'}.get(res, 'n/a')
    bench = b.benchmark_symbol or BENCH
    local = not is_us_listing(b.symbol)
    reason = (f'{b.symbol} {r * 100:+.2f} % vs {bench} {rb * 100:+.2f} % → exceso '
              f'{ex * 100:+.2f} % (banda ±{b.band * 100:.1f} %) · postura {_STANCE_ES.get(b.stance, b.stance)} → {verdict}'
              + (' · retorno en moneda local (sin ajuste cambiario)' if local else ''))
    reason_en = (f'{b.symbol} {r * 100:+.2f}% vs {bench} {rb * 100:+.2f}% → excess '
                 f'{ex * 100:+.2f}% (band ±{b.band * 100:.1f}%) · {b.stance} stance → {res}'
                 + (' · local-currency return (not FX-adjusted)' if local else ''))
    return {'result': res, 'reason': reason, 'reason_en': reason_en, 'base_date': p0[0], 'base_price': p0[1],
            'eval_date': p1[0], 'eval_price': p1[1], 'bench_base_price': b0[1], 'bench_eval_price': b1[1],
            'asset_return': round(r, 6), 'bench_return': round(rb, 6), 'excess_return': round(ex, 6),
            'price_source': 'cierres diarios ajustados' + (' (moneda local)' if local else '')}


CLOSE_BUFFER_MIN = 30      # el cierre de hoy cuenta desde las 16:30 de Nueva York


def session_in_progress(now):
    """¿La sesión de HOY todavía no cerró? (entonces la barra de hoy es un precio en curso)."""
    ny = _ny_datetime(now)
    return ny.weekday() < 5 and (ny.hour * 60 + ny.minute) < 16 * 60 + CLOSE_BUFFER_MIN


def evaluate_due(session, now=None, price_fn=None, limit=500):
    """Califica los checkpoints vencidos con PRECIOS REALES. Idempotente.
    price_fn(símbolo, desde: date) -> {'YYYY-MM-DD': cierre ajustado} | None."""
    now = now or _now()
    today = market_date(now)
    price_fn = price_fn or default_price_fn
    created = ensure_baselines(session)
    done = {(cid, cp) for cid, cp in session.query(ClaimOutcome.claim_id, ClaimOutcome.checkpoint).all()}
    due, pending = [], 0
    for b in session.query(ClaimBaseline).all():
        for cp in (b.checkpoints or []):
            if (b.claim_id, cp['label']) in done:
                continue
            if date.fromisoformat(cp['due_date']) >= today:
                pending += 1
                continue
            due.append((b, cp))
    due.sort(key=lambda x: x[1]['due_date'])
    pending += max(0, len(due) - limit)
    due = due[:limit]
    status = {c.id: c.status for c in session.query(ResearchClaim.id, ResearchClaim.status)
              .filter(ResearchClaim.id.in_({b.claim_id for b, _ in due})).all()} if due else {}
    # Ventana de precios: la MÁS ANTIGUA que necesite cualquier checkpoint del lote
    # para ese símbolo (SPY la comparten todas). Si se pidiera con la del primer
    # checkpoint procesado, un final de 365 días quedaría fuera de la serie.
    need = {}
    for b, _cp in due:
        if not b.scoreable:
            continue
        since = date.fromisoformat(b.baseline_date) - timedelta(days=15)
        for sym in (b.symbol, b.benchmark_symbol or BENCH):
            if sym and (sym not in need or since < need[sym]):
                need[sym] = since
    live_bar = today.isoformat() if session_in_progress(now) else None
    cache = {}

    def get_series(sym, since):
        want = min(since, need.get(sym, since))
        hit = cache.get(sym)
        if hit is None or want < hit[0]:
            try:
                ser = price_fn(sym, want)
            except Exception as e:  # noqa: BLE001
                log.warning('outcomes: precios %s: %s', sym, type(e).__name__)
                ser = None
            if ser and live_bar and live_bar in ser:
                # barra de HOY con la sesión abierta = precio en curso, no un cierre
                ser = {k: v for k, v in ser.items() if k != live_bar}
            cache[sym] = hit = (want, ser)
        return hit[1]

    counts = {'hit': 0, 'miss': 0, 'n/a': 0}
    evaluated = 0
    for b, cp in due:
        res = score_checkpoint(b, cp, get_series, today)
        if res is None:
            pending += 1
            continue
        row = ClaimOutcome(
            claim_id=b.claim_id, baseline_id=b.id, entity_id=b.entity_id, agent_type=b.agent_type,
            horizon=b.horizon, stance=b.stance, confidence=b.confidence, checkpoint=cp['label'],
            checkpoint_days=cp['days'], final=bool(cp.get('final')), due_date=cp['due_date'], symbol=b.symbol,
            base_date=res.get('base_date'), base_price=res.get('base_price'), eval_date=res.get('eval_date'),
            eval_price=res.get('eval_price'), bench_base_price=res.get('bench_base_price'),
            bench_eval_price=res.get('bench_eval_price'), asset_return=res.get('asset_return'),
            bench_return=res.get('bench_return'), excess_return=res.get('excess_return'), band=b.band,
            result=res['result'], reason=(res.get('reason') or '')[:900],
            reason_en=(res.get('reason_en') or '')[:900] or None, claim_status=status.get(b.claim_id),
            price_source=res.get('price_source'), method=METHOD, evaluated_at=now)
        try:
            with session.begin_nested():
                session.add(row)
                session.flush()
        except IntegrityError:        # otro proceso la calificó a la vez → idempotente
            continue
        evaluated += 1
        counts[res['result']] = counts.get(res['result'], 0) + 1
    snap = None
    if evaluated:
        invalidate_cache()
    if evaluated or not _snapshot_today(session, now):
        try:
            snap = store_snapshot(session, now=now)
        except Exception as e:  # noqa: BLE001
            log.warning('outcomes: snapshot: %s', type(e).__name__)
    session.flush()
    return {'evaluated': evaluated, 'pending': pending, 'hits': counts['hit'], 'misses': counts['miss'],
            'n_a': counts['n/a'], 'baselines_created': created, 'as_of': now.isoformat(),
            'snapshot': bool(snap)}


# ── historial (track record) y calibración ──────────────────────────────────
def bucket_index(conf):
    c = max(0.0, min(1.0, float(conf or 0)))
    return min(len(BUCKETS) - 1, int(c * len(BUCKETS)))


def bucket_label(i):
    lo, hi = BUCKETS[i]
    return f'{lo:.1f}-{hi:.1f}'


def stats(rows):
    """rows: [(confianza, 1|0)] → n, aciertos, tasa, Brier y tramos de fiabilidad."""
    n = len(rows)
    hits = sum(y for _c, y in rows)
    cal = []
    for i, (lo, hi) in enumerate(BUCKETS):
        br = [(c, y) for c, y in rows if bucket_index(c) == i]
        nb = len(br)
        cal.append({'bucket': bucket_label(i), 'lo': lo, 'hi': hi, 'n': nb, 'hits': sum(y for _c, y in br),
                    'mean_conf': round(sum(c for c, _y in br) / nb, 4) if nb else None,
                    'hit_rate': round(sum(y for _c, y in br) / nb, 4) if nb else None})
    return {'n_scored': n, 'hits': hits, 'hit_rate': round(hits / n, 4) if n else None,
            'brier': round(sum((c - y) ** 2 for c, y in rows) / n, 4) if n else None,
            'calibration': cal}


def reliability(hits, n, k=None):
    """Fiabilidad del agente con encogimiento hacia 0.5 (neutral sin historia)."""
    k = k_default() if k is None else k
    return round((hits + k * PRIOR_RELIABILITY) / (n + k), 4) if (n + k) > 0 else PRIOR_RELIABILITY


def track_record(session, agent_type=None):
    """Historial por agente sobre checkpoints FINALES (+ señal temprana aparte)."""
    q = session.query(ClaimOutcome.agent_type, ClaimOutcome.confidence, ClaimOutcome.result,
                      ClaimOutcome.final, ClaimOutcome.claim_status)
    if agent_type:
        q = q.filter(ClaimOutcome.agent_type == agent_type)
    finals, interim, na = {}, {}, {}
    for at, conf, res, final, cst in q.all():
        if cst == 'retracted':
            continue          # retirada por cifras sin respaldo: su confianza se basó en datos malos
        if res == 'n/a':
            na[at] = na.get(at, 0) + 1
            continue
        y = 1 if res == 'hit' else 0
        (finals if final else interim).setdefault(at, []).append((float(conf or 0), y))
    k = k_default()
    types = sorted(set(finals) | set(interim) | set(na) | ({agent_type} if agent_type else set()))
    agents = []
    all_rows = []
    for at in types:
        st = stats(finals.get(at, []))
        all_rows += finals.get(at, [])
        it = interim.get(at, [])
        agents.append(dict(st, agent_type=at, n_na=na.get(at, 0),
                           reliability=reliability(st['hits'], st['n_scored'], k),
                           sufficient=st['n_scored'] >= MIN_N,
                           interim={'n_scored': len(it), 'hits': sum(y for _c, y in it),
                                    'hit_rate': round(sum(y for _c, y in it) / len(it), 4) if it else None}))
    overall = stats(all_rows)
    overall.update(n_na=sum(na.values()), sufficient=overall['n_scored'] >= MIN_N,
                   reliability=reliability(overall['hits'], overall['n_scored'], k))
    return {'agents': agents, 'overall': overall, 'as_of': _now().isoformat(), 'method': CAL_METHOD,
            'basis': 'final_checkpoints', 'band': band_default(), 'k': k, 'min_n': MIN_N,
            'benchmark': BENCH}


_CACHE = {'table': None, 'ts': 0.0}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL = 600


def invalidate_cache():
    with _CACHE_LOCK:
        _CACHE['table'], _CACHE['ts'] = None, 0.0


def calibration_table(session=None, force=False):
    """{agent_type: {n, hits, buckets: [[n, aciertos] × 5]}} (finales). Caché 10 min."""
    with _CACHE_LOCK:
        if not force and _CACHE['table'] is not None and time.time() - _CACHE['ts'] < _CACHE_TTL:
            return _CACHE['table']
    if session is None:
        return _CACHE['table'] or {}
    tr = track_record(session)
    table = {a['agent_type']: {'n': a['n_scored'], 'hits': a['hits'],
                               'buckets': [[b['n'], b['hits']] for b in a['calibration']]}
             for a in tr['agents']}
    with _CACHE_LOCK:
        _CACHE['table'], _CACHE['ts'] = table, time.time()
    return table


def calibration_detail(agent_type, raw, session=None, table=None, k=None):
    """Confianza calibrada con su cuenta (auditable)."""
    k = k_default() if k is None else k
    raw = max(0.0, min(1.0, float(raw or 0)))
    t = table if table is not None else calibration_table(session)
    a = (t or {}).get(agent_type) or {}
    i = bucket_index(raw)
    bk = a.get('buckets') or [[0, 0]] * len(BUCKETS)
    n_b, h_b = (bk[i] if i < len(bk) else [0, 0])
    cal = (h_b + k * raw) / (n_b + k) if (n_b + k) > 0 else raw
    return {'raw': round(raw, 4), 'calibrated': round(cal, 4), 'bucket': bucket_label(i), 'n_bucket': n_b,
            'hits_bucket': h_b, 'k': k, 'sufficient': n_b >= MIN_N, 'agent_n': a.get('n', 0),
            'method': CAL_METHOD + ' (encogimiento bayesiano)'}


def calibrated_confidence(agent_type, raw, session=None, table=None, k=None):
    """Número calibrado (0-1): (aciertos_tramo + k·cruda)/(n_tramo + k)."""
    return calibration_detail(agent_type, raw, session=session, table=table, k=k)['calibrated']


def agent_reliability(agent_type, session=None, table=None, k=None):
    t = table if table is not None else calibration_table(session)
    a = (t or {}).get(agent_type) or {}
    return reliability(a.get('hits', 0), a.get('n', 0), k)


def _snapshot_today(session, now):
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return session.query(CalibrationSnapshot.id).filter(CalibrationSnapshot.as_of >= start).first() is not None


def store_snapshot(session, now=None):
    """Guarda la foto del historial (una fila por agente + global)."""
    now = now or _now()
    tr = track_record(session)
    rows = [CalibrationSnapshot(as_of=now, agent_type=None, n_scored=tr['overall']['n_scored'],
                                hits=tr['overall']['hits'], hit_rate=tr['overall']['hit_rate'],
                                brier=tr['overall']['brier'], reliability=tr['overall']['reliability'],
                                buckets=tr['overall']['calibration'], method=CAL_METHOD)]
    for a in tr['agents']:
        rows.append(CalibrationSnapshot(as_of=now, agent_type=a['agent_type'], n_scored=a['n_scored'],
                                        hits=a['hits'], hit_rate=a['hit_rate'], brier=a['brier'],
                                        reliability=a['reliability'], buckets=a['calibration'],
                                        method=CAL_METHOD))
    session.add_all(rows)
    session.flush()
    return len(rows)


def snapshots(session, agent_type=None, limit=60):
    q = session.query(CalibrationSnapshot)
    q = q.filter(CalibrationSnapshot.agent_type == agent_type) if agent_type else q.filter(
        CalibrationSnapshot.agent_type.is_(None))
    rows = q.order_by(CalibrationSnapshot.as_of.desc()).limit(limit).all()
    return [{'as_of': r.as_of.isoformat() if r.as_of else None, 'agent_type': r.agent_type,
             'n_scored': r.n_scored, 'hits': r.hits, 'hit_rate': r.hit_rate, 'brier': r.brier,
             'reliability': r.reliability} for r in reversed(rows)]


def outcomes_for_claim(session, claim_id):
    rows = (session.query(ClaimOutcome).filter(ClaimOutcome.claim_id == claim_id)
            .order_by(ClaimOutcome.checkpoint_days).all())
    return [{'checkpoint': r.checkpoint, 'final': r.final, 'due_date': r.due_date, 'result': r.result,
             'reason': r.reason, 'reason_en': r.reason_en, 'excess_return': r.excess_return, 'asset_return': r.asset_return,
             'bench_return': r.bench_return, 'base_date': r.base_date, 'eval_date': r.eval_date,
             'evaluated_at': r.evaluated_at.isoformat() if r.evaluated_at else None} for r in rows]


def recent_outcomes(session, limit=30, agent_type=None):
    q = session.query(ClaimOutcome)
    if agent_type:
        q = q.filter(ClaimOutcome.agent_type == agent_type)
    rows = q.order_by(ClaimOutcome.evaluated_at.desc()).limit(limit).all()
    return [{'claim_id': r.claim_id, 'entity_id': r.entity_id, 'agent_type': r.agent_type,
             'horizon': r.horizon, 'stance': r.stance, 'confidence': r.confidence, 'checkpoint': r.checkpoint,
             'final': r.final, 'result': r.result, 'reason': r.reason, 'reason_en': r.reason_en,
             'excess_return': r.excess_return, 'symbol': r.symbol,
             'evaluated_at': r.evaluated_at.isoformat() if r.evaluated_at else None} for r in rows]
