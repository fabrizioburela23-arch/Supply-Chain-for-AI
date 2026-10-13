"""core/prices_store.py — LA MEMORIA DE LOS NÚMEROS (docs/BRECHAS_V2.md bloque 2; ARQUITECTURA_V2 §9.1, §20.1 #1-#3).

Khipus guarda su propia historia diaria: precios EOD (con volumen y cierre ajustado), tipo de cambio diario,
foto diaria de métricas por empresa y de posiciones. Lectura ÚNICA para el riesgo, los técnicos y la volatilidad
histórica: `history()` lee primero la base y, si no cubre el rango pedido (o no hay base), quien llama usa la
descarga en vivo de siempre (core/risk_report.fetch_history). Sin DATABASE_URL todo queda como antes.

Escrituras (append-only: nunca UPDATE/DELETE; core/ledger_ddl lo impide en la base):
  · `ingest_series` — inserta las fechas nuevas (ON CONFLICT DO NOTHING) y, si al re-bajar una ventana los
    cierres AJUSTADOS de fechas ya guardadas cambiaron (split o dividendo), agrega una fila en price_adjustments
    con el factor: al leer, las filas guardadas ANTES de esa detección y con fecha anterior se multiplican por él.
  · `ingest_fx` — tipo de cambio diario {CUR}USD=X.
  · `snapshot_daily` — metrics_eod (NRS, grado de flujo, cierre, capitalización) y positions_eod (eco_pos /
    kh_portfolios de cada dueño sincronizado + posiciones de las cuentas de corretaje).

Trabajos:
  · diario (core/scheduler, `daily_tick`): días hábiles después de las 22:00 UTC (todas las bolsas cerradas),
    ~600 pedidos pequeños (1 mes) con pausa entre pedidos, en un hilo propio; corta si la fuente cae.
  · relleno de 5 años (BRECHAS #3 SIN responder → SOLO a pedido del operador con PIN: POST /api/prices/backfill):
    reanudable (salta lo ya cubierto), con pausa entre pedidos, progreso en GET /api/prices/backfill y una
    decisión 'data.backfill' al empezar, al detenerlo y al terminar. NUNCA corre solo.

Nada aquí llama a la IA. La red se inyecta (`getter`) para las pruebas.
"""
import logging
import math
import os
import threading
import time
from datetime import date, datetime, timedelta, timezone

log = logging.getLogger('khipu')

SOURCE = 'yahoo'
CHART_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/{sym}'
RANGE_DAYS = {'5d': 7, '1mo': 31, '3mo': 92, '6mo': 183, '1y': 366, '2y': 731, '5y': 1827, '10y': 3653}
STALE_DAYS = 5               # la última fila guardada no puede tener más de 5 días (fin de semana + feriado)
COVER_SLACK_DAYS = 10        # la primera fila puede empezar hasta 10 días después del inicio pedido
ADJ_TOL = 5e-4               # 0,05 %: diferencia entre cierres ajustados que cuenta como split/dividendo
EOD_HOUR_UTC = 22            # todas las bolsas (también las de América) ya cerraron
SOURCE_DOWN_AFTER = 12       # fallos SEGUIDOS → la fuente se da por caída y la corrida se detiene
SOURCE_PAUSE_S = 3600
MAX_YEARS = 5
MAX_GAP_DAYS = 12            # hueco máximo entre dos cierres guardados seguidos (Año Nuevo chino / Golden Week ≈ 11 días);
                             # uno mayor = la descarga faltó: la serie NO se da por completa (revisión batch E)
SNAPSHOT_MAX_AGE_DAYS = 7    # la foto diaria solo usa un cierre/FX de hasta 7 días; más viejo → NULL (no inventar)
DAILY_REPAIR_AFTER_DAYS = 25 # el diario re-baja un rango MAYOR (hasta 1 año) si lo último guardado es más viejo


def _env_float(name, default, lo, hi):
    try:
        v = float(os.getenv(name, default))
    except (TypeError, ValueError):
        v = default
    return max(lo, min(hi, v))


def req_interval_s():
    """Pausa mínima entre pedidos a la fuente (PRICES_REQ_INTERVAL_S, por defecto 0,6 s)."""
    return _env_float('PRICES_REQ_INTERVAL_S', 0.6, 0.0, 30.0)


def daily_enabled():
    return (os.getenv('PRICES_EOD') or 'on').strip().lower() not in ('off', '0', 'false', 'no')


def db_on():
    try:
        from ontology.db import ontology_available
        return ontology_available()
    except Exception:  # noqa: BLE001
        return False


_READ_PAUSE = {'until': 0.0, 'error': None}
READ_PAUSE_S = 60.0


def _reads_paused():
    """Base configurada pero caída: cada lectura esperaría el connect_timeout (5 s) → tras un fallo, 60 s sin
    intentar (el riesgo y los técnicos usan la descarga en vivo mientras tanto)."""
    return time.time() < _READ_PAUSE['until']


def _read_failed(e):
    _READ_PAUSE.update(until=time.time() + READ_PAUSE_S, error=type(e).__name__)


def _now():
    return datetime.now(timezone.utc)


def _d(v):
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    return date.fromisoformat(str(v)[:10])


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _zone(name):
    """ZoneInfo de la bolsa (meta.exchangeTimezoneName) o None si no se conoce."""
    if not name:
        return None
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(str(name))
    except Exception:  # noqa: BLE001 — zona desconocida o sin tzdata: se usa gmtoffset
        return None


# ── red: descarga del gráfico diario de Yahoo ────────────────────────────────
class _Pacer:
    """Respeta una pausa mínima entre pedidos (compartida por el diario y el relleno)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self, interval, sleep=time.sleep):
        with self._lock:
            gap = self._last + interval - time.monotonic()
            if gap > 0:
                sleep(gap)
            self._last = time.monotonic()


PACER = _Pacer()


def _default_getter():
    from core.company_data import _get_json
    return _get_json


def fetch_chart(symbol, rng='1mo', getter=None, now=None, years=None):
    """→ {'rows': [{date, open, high, low, close, adj_close, volume}], currency, tz, error}. La vela de la sesión
    que todavía NO cerró se descarta (append-only: un cierre parcial guardado quedaría para siempre)."""
    getter = getter or _default_getter()
    now = now or _now()
    params = {'interval': '1d', 'events': 'div,splits'}
    if years:
        params.update(period1=int((now - timedelta(days=int(years * 365.25) + 3)).timestamp()),
                      period2=int(now.timestamp()))
    else:
        params['range'] = rng
    data, err = getter(CHART_URL.format(sym=symbol), params=params, timeout=15)
    if err or not isinstance(data, dict):
        return {'rows': [], 'currency': None, 'tz': None, 'error': str(err or 'invalid')}
    res = ((data.get('chart') or {}).get('result') or [None])[0] or {}
    meta = res.get('meta') or {}
    ts = res.get('timestamp') or []
    q = ((res.get('indicators') or {}).get('quote') or [{}])[0] or {}
    adj = ((res.get('indicators') or {}).get('adjclose') or [{}])[0] or {}
    adj = adj.get('adjclose') if isinstance(adj, dict) else None
    try:
        off = int(meta.get('gmtoffset') or 0)
    except (TypeError, ValueError):
        off = 0
    zone = _zone(meta.get('exchangeTimezoneName'))

    def local_date(t):
        # la fecha de la BOLSA con la zona horaria REAL de cada instante (horario de verano incluido); gmtoffset es
        # el desfase de HOY y fecharía mal las filas del otro semestre (FX de Londres: un día antes en verano)
        if zone is not None:
            return datetime.fromtimestamp(float(t), tz=zone).date()
        return datetime.fromtimestamp(float(t) + off, tz=timezone.utc).date()
    # sesión en curso: si ahora < fin de la sesión regular, su vela es parcial
    open_day = None
    reg = ((meta.get('currentTradingPeriod') or {}).get('regular') or {})
    try:
        if reg.get('end') and now.timestamp() < float(reg['end']):
            open_day = local_date(float(reg.get('start') or reg['end']))
    except (TypeError, ValueError, OverflowError, OSError):
        open_day = None
    local_today = local_date(now.timestamp())
    has_period = bool(reg.get('end'))
    cols = {k: (q.get(k) or []) for k in ('open', 'high', 'low', 'close', 'volume')}
    adj = adj or []

    def at(lst, i):
        return lst[i] if i < len(lst) else None
    rows = []
    for i, t in enumerate(ts):
        try:
            d = local_date(int(t))
        except (TypeError, ValueError, OverflowError, OSError):
            continue
        if (open_day is not None and d >= open_day) or (not has_period and d >= local_today):
            continue
        c = _f(at(cols['close'], i))
        if c is None or c <= 0:
            continue
        a = _f(at(adj, i))
        v = at(cols['volume'], i)
        # sin cierre ajustado de Yahoo → adj_close NULL (al leer vale el cierre y la serie sale como NO ajustada;
        # antes se guardaba el cierre crudo como "ajustado" y el aviso del reporte de riesgo se perdía)
        rows.append({'date': d, 'open': _f(at(cols['open'], i)), 'high': _f(at(cols['high'], i)),
                     'low': _f(at(cols['low'], i)), 'close': c, 'adj_close': a if (a is not None and a > 0) else None,
                     'volume': int(v) if isinstance(v, (int, float)) and math.isfinite(v) else None})
    dedup = {}
    for r in rows:
        dedup[r['date']] = r            # Yahoo a veces repite el último día: gana el último
    return {'rows': [dedup[k] for k in sorted(dedup)], 'currency': meta.get('currency'),
            'tz': meta.get('exchangeTimezoneName'), 'error': None if dedup else 'empty'}


# ── escritura ────────────────────────────────────────────────────────────────
def _effective(rows, adjs):
    """{date: adj efectivo} de filas guardadas [(date, adj, ingested_at)] con los factores de price_adjustments."""
    out = {}
    for d, a, ing in rows:
        f = 1.0
        for bd, fac, det in adjs:
            if ing < det and d < bd:
                f *= fac
        out[d] = a * f
    return out


def _load_adjs(session, instrument_id, source):
    from sqlalchemy import text
    return [(r[0], float(r[1]), r[2]) for r in session.execute(text(
        'SELECT before_date, factor, detected_at FROM price_adjustments WHERE instrument_id = :i AND source = :s'),
        {'i': instrument_id, 's': source}).all()]


def detect_adjustments(stored_eff, fetched, tol=ADJ_TOL):
    """Compara la ventana re-bajada con lo guardado (ya ajustado). → [(before_date, factor, evidence)].
    Recorre las fechas comunes de la más nueva a la más vieja: cada salto del cociente nuevo/guardado es un evento
    (split o dividendo) que vale para las fechas ANTERIORES a la fecha siguiente bajada."""
    fdates = sorted(r['date'] for r in fetched)
    new = {r['date']: r['adj_close'] for r in fetched if r.get('adj_close')}
    common = sorted((d for d in new if d in stored_eff and stored_eff[d]), reverse=True)
    out, cum = [], 1.0
    for d in common:
        r = new[d] / stored_eff[d]
        if abs(r / cum - 1.0) > tol:
            later = [x for x in fdates if x > d]
            before = later[0] if later else d + timedelta(days=1)
            out.append((before, r / cum, {'date': d.isoformat(), 'stored': round(stored_eff[d], 6),
                                          'fetched': round(new[d], 6)}))
            cum = r
    return out


def ingest_series(session, instrument_id, fetched, currency=None, source=SOURCE):
    """Inserta las fechas nuevas y registra los ajustes detectados. Idempotente. → {inserted, adjustments}."""
    from sqlalchemy import text
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from ontology.history_models import PriceAdjustment, PriceEOD
    if not fetched:
        return {'inserted': 0, 'adjustments': 0}
    lo, hi = min(r['date'] for r in fetched), max(r['date'] for r in fetched)
    stored = session.execute(text(
        'SELECT date, adj_close, ingested_at FROM prices_eod WHERE instrument_id = :i AND source = :s '
        'AND date BETWEEN :lo AND :hi'), {'i': instrument_id, 's': source, 'lo': lo, 'hi': hi}).all()
    n_adj = 0
    if stored:
        eff = _effective([(r[0], float(r[1]), r[2]) for r in stored if r[1] is not None],
                         _load_adjs(session, instrument_id, source))
        for before, factor, ev in detect_adjustments(eff, fetched):
            session.execute(pg_insert(PriceAdjustment.__table__).values(
                instrument_id=instrument_id, source=source, before_date=before, factor=factor, evidence=ev))
            n_adj += 1
    have = {r[0] for r in stored}
    rows = [{'instrument_id': instrument_id, 'source': source, 'date': r['date'], 'open': r.get('open'),
             'high': r.get('high'), 'low': r.get('low'), 'close': r['close'], 'adj_close': r['adj_close'],
             'volume': r.get('volume'), 'currency': (currency or None)} for r in fetched if r['date'] not in have]
    ins = 0
    for i in range(0, len(rows), 500):
        res = session.execute(pg_insert(PriceEOD.__table__).values(rows[i:i + 500]).on_conflict_do_nothing()
                              .returning(PriceEOD.__table__.c.date))
        ins += len(res.fetchall())
    return {'inserted': ins, 'adjustments': n_adj}


def ingest_fx(session, ccy, fetched, source=SOURCE):
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from ontology.history_models import FxDaily
    rows = [{'ccy': ccy, 'source': source, 'date': r['date'], 'rate_to_usd': r['close']}
            for r in fetched or [] if r.get('close')]
    ins = 0
    for i in range(0, len(rows), 500):
        res = session.execute(pg_insert(FxDaily.__table__).values(rows[i:i + 500]).on_conflict_do_nothing()
                              .returning(FxDaily.__table__.c.date))
        ins += len(res.fetchall())
    return ins


# ── lectura ──────────────────────────────────────────────────────────────────
def load_series(session, instrument_id, start=None, source=SOURCE):
    """[{date, close, adj, volume, currency}] ordenado, con los ajustes aplicados."""
    from sqlalchemy import text
    q = ('SELECT date, close, adj_close, volume, currency, ingested_at FROM prices_eod '
         'WHERE instrument_id = :i AND source = :s' + (' AND date >= :st' if start else '') + ' ORDER BY date')
    rows = session.execute(text(q), {'i': instrument_id, 's': source, 'st': start}).all()
    if not rows:
        return []
    adjs = _load_adjs(session, instrument_id, source)
    eff = _effective([(r[0], float(r[2] if r[2] is not None else r[1]), r[5]) for r in rows], adjs)
    return [{'date': r[0], 'close': float(r[1]) if r[1] is not None else None, 'adj': eff[r[0]],
             'adjusted': r[2] is not None, 'volume': r[3], 'currency': r[4]} for r in rows]


def max_gap_days(dates):
    """El mayor salto en días de calendario entre dos fechas seguidas (0 con menos de dos)."""
    ds = sorted(dates)
    return max(((b - a).days for a, b in zip(ds, ds[1:])), default=0)


def _covers(rows, start, today, days):
    """¿La serie guardada cubre el rango SIN huecos? Primera fila cerca del inicio, última al día, suficientes filas
    y ningún salto mayor que MAX_GAP_DAYS (revisión batch E: con un hueco de 3 meses la serie pasaba y el riesgo
    convertía el hueco en UN rendimiento "diario" del 14 %)."""
    if not rows:
        return False
    first, last = rows[0]['date'], rows[-1]['date']
    need = int(days * 252 / 365 * 0.55)
    return first <= start + timedelta(days=COVER_SLACK_DAYS) and last >= today - timedelta(days=STALE_DAYS) \
        and len(rows) >= max(3, need) and max_gap_days(r['date'] for r in rows) <= MAX_GAP_DAYS


def history(symbol, rng='1y', today=None):
    """DB primero: ({'YYYY-MM-DD': cierre ajustado}, moneda, meta{source, as_of, adjusted, n, from}) si la base
    cubre el rango pedido y está al día; None si no (quien llama baja en vivo). Nunca lanza."""
    days = RANGE_DAYS.get(rng)
    if not days or not db_on() or _reads_paused():
        return None
    today = today or _now().date()
    start = today - timedelta(days=days)
    try:
        from ontology.db import session_scope
        with session_scope() as s:
            rows = load_series(s, str(symbol).upper()[:32], start=start)
    except Exception as e:  # noqa: BLE001 — tablas ausentes, base caída: respaldo en vivo
        log.debug('prices_store.history %s: %s', symbol, type(e).__name__)
        _read_failed(e)
        return None
    if not _covers(rows, start, today, days):
        return None
    cur = next((r['currency'] for r in reversed(rows) if r['currency']), None)
    out = {r['date'].isoformat(): r['adj'] for r in rows if r['adj'] and r['adj'] > 0}
    adjusted = all(r.get('adjusted', True) for r in rows)      # una fila sin ajuste de Yahoo → serie NO ajustada
    return out, cur, {'source': f'khipus_eod:{SOURCE}', 'as_of': rows[-1]['date'].isoformat(), 'adjusted': adjusted,
                      'n': len(out), 'from': rows[0]['date'].isoformat()}


def fx_history(ccy, rng='1y', today=None):
    """({'YYYY-MM-DD': tasa ccy→USD}, meta) desde fx_daily si cubre el rango; None si no."""
    days = RANGE_DAYS.get(rng)
    if not days or not db_on() or not ccy or ccy == 'USD' or _reads_paused():
        return None
    today = today or _now().date()
    start = today - timedelta(days=days)
    try:
        from sqlalchemy import text

        from ontology.db import session_scope
        with session_scope() as s:
            rows = s.execute(text('SELECT date, rate_to_usd FROM fx_daily WHERE ccy = :c AND source = :s '
                                  'AND date >= :st ORDER BY date'), {'c': ccy, 's': SOURCE, 'st': start}).all()
    except Exception as e:  # noqa: BLE001
        _read_failed(e)
        return None
    rr = [{'date': r[0]} for r in rows]
    if not _covers(rr, start, today, days):
        return None
    return ({r[0].isoformat(): float(r[1]) for r in rows},
            {'source': f'khipus_fx:{SOURCE}', 'as_of': rows[-1][0].isoformat(), 'n': len(rows)})


def status():
    """Resumen para el 🩺 y /api/prices/status (sin red)."""
    out = {'db': db_on(), 'daily_enabled': daily_enabled(), 'daily': dict(_DAILY), 'backfill': backfill_state(),
           'req_interval_s': req_interval_s()}
    out['daily'].pop('thread', None)
    if not out['db']:
        return out
    try:
        from sqlalchemy import text

        from ontology.db import session_scope
        with session_scope() as s:
            r = s.execute(text('SELECT count(*), count(DISTINCT instrument_id), max(date), min(date) FROM prices_eod')).first()
            f = s.execute(text('SELECT count(*), count(DISTINCT ccy), max(date) FROM fx_daily')).first()
            i = s.execute(text("SELECT count(*), count(*) FILTER (WHERE review IS NOT NULL) FROM instruments")).first()
            m = s.execute(text('SELECT max(date) FROM metrics_eod')).scalar()
            p = s.execute(text('SELECT max(date), count(DISTINCT owner_hash) FROM positions_eod')).first()
            a = s.execute(text('SELECT count(*) FROM price_adjustments')).scalar()
        out.update(rows=int(r[0]), instruments_with_prices=int(r[1]), last_date=r[2] and r[2].isoformat(),
                   first_date=r[3] and r[3].isoformat(), fx_rows=int(f[0]), fx_pairs=int(f[1]),
                   fx_last=f[2] and f[2].isoformat(), instruments=int(i[0]), instruments_review=int(i[1]),
                   metrics_last=m and m.isoformat(), positions_last=p[0] and p[0].isoformat(),
                   positions_owners=int(p[1] or 0), adjustments=int(a or 0))
    except Exception as e:  # noqa: BLE001
        out['error'] = type(e).__name__
    return out


# ── corrida (diaria o relleno) ───────────────────────────────────────────────
def _targets(session, symbols=None):
    """(equities, fx): instrumentos a bajar. Siembra los que falten primero."""
    from sqlalchemy import text

    from core import instruments
    instruments.seed(session)
    rows = session.execute(text('SELECT id, kind, currency, note FROM instruments ORDER BY id')).all()
    want = {str(x).upper() for x in symbols} if symbols else None
    eq = [r[0] for r in rows if r[1] != 'fx' and (want is None or r[0] in want)]
    fx = [((r[3] or {}).get('ccy') or r[0][:3]) for r in rows if r[1] == 'fx' and (want is None or r[0] in want)]
    first = [s for s in ('SPY', '^IRX') if s in eq]
    return first + [s for s in eq if s not in first], fx


def _coverage(session, instrument_id, table='prices_eod'):
    from sqlalchemy import text
    """(primera fecha, última, filas, mayor hueco en días entre dos filas seguidas)."""
    if table == 'fx_daily':
        sql, key = 'SELECT date FROM fx_daily WHERE ccy = :i AND source = :s', 'ccy'
    else:
        sql, key = 'SELECT date FROM prices_eod WHERE instrument_id = :i AND source = :s', 'instrument_id'
    r = session.execute(text(
        f'SELECT min(date), max(date), count(*), coalesce(max(date - prev), 0) FROM ('
        f'SELECT date, lag(date) OVER (ORDER BY date) AS prev FROM ({sql}) x) y'), {'i': instrument_id, 's': SOURCE}).first()
    return (r[0], r[1], int(r[2] or 0), int(r[3] or 0)) if r else (None, None, 0, 0)


def _one(sym, is_fx, *, rng, years, getter, state, sleep, interval, now, stop):
    """Baja e ingiere UN instrumento con reintentos ante 429/5xx. Devuelve True/False (éxito)."""
    from ontology.db import session_scope
    url_sym = f'{sym}USD=X' if is_fx else sym
    if years:
        with session_scope() as s:
            mn, _mx, n, gap = _coverage(s, sym, 'fx_daily' if is_fx else 'prices_eod')
        target = (now - timedelta(days=int(years * 365.25))).date()
        # reanudable: se salta lo que YA está completo; con un hueco en el medio se vuelve a bajar todo el rango (la
        # inserción es idempotente: solo entran las fechas que faltan) — antes solo miraba la fecha más vieja
        if mn is not None and mn <= target + timedelta(days=COVER_SLACK_DAYS) and gap <= MAX_GAP_DAYS:
            state['skipped'] += 1
            return True
    elif rng == '1mo':
        # diario: si lo último guardado tiene más de ~25 días (fuente caída, PRICES_EOD=off un tiempo), 1 mes dejaría
        # un hueco permanente → se baja el rango que lo cubre (hasta 1 año; los 5 años siguen siendo solo a pedido)
        with session_scope() as s:
            _mn, mx, _n, _gap = _coverage(s, sym, 'fx_daily' if is_fx else 'prices_eod')
        if mx is not None:
            behind = (now.date() - mx).days
            if behind > DAILY_REPAIR_AFTER_DAYS:
                rng = next((k for k in ('3mo', '6mo', '1y') if RANGE_DAYS[k] >= behind + 7), '1y')
                state['repaired'] = state.get('repaired', 0) + 1
    for attempt in range(3):
        if stop():
            return False
        PACER.wait(interval, sleep)
        got = fetch_chart(url_sym, rng, getter=getter, now=now, years=years)
        err = got.get('error')
        if err in (None, 'empty'):
            break
        if any(c in str(err) for c in ('429', ' 50', 'timeout', 'Connection')) and attempt < 2:
            sleep(min(30.0, 3.0 * (2 ** attempt)))
            continue
        break
    if got.get('error') and got['error'] != 'empty':
        state['failed'] += 1
        state['consecutive_fail'] += 1
        if len(state['errors']) < 20:
            state['errors'].append(f'{url_sym}: {got["error"]}'[:120])
        return False
    state['consecutive_fail'] = 0
    if not got['rows']:
        state['empty'] += 1
        return True
    with session_scope() as s:
        if is_fx:
            state['rows'] += ingest_fx(s, sym, got['rows'])
        else:
            r = ingest_series(s, sym, got['rows'], currency=got.get('currency'))
            state['rows'] += r['inserted']
            state['adjustments'] += r['adjustments']
    state['ok'] += 1
    return True


def _run(state, *, rng='1mo', years=None, symbols=None, getter=None, sleep=time.sleep, now=None, interval=None):
    """Corrida completa sobre todos los instrumentos (o `symbols`). Llena `state` en vivo (progreso)."""
    from ontology.db import session_scope
    now = now or _now()
    interval = req_interval_s() if interval is None else interval
    with session_scope() as s:
        eq, fx = _targets(s, symbols)
    items = [(c, True) for c in fx] + [(e, False) for e in eq]
    state.update(total=len(items), done=0, ok=0, skipped=0, failed=0, empty=0, rows=0, adjustments=0, repaired=0,
                 consecutive_fail=0, errors=[], current=None, stopped_reason=None)
    for sym, is_fx in items:
        if state.get('stop'):
            state['stopped_reason'] = 'stopped_by_operator'
            break
        state['current'] = f'{sym}USD=X' if is_fx else sym
        try:
            _one(sym, is_fx, rng=rng, years=years, getter=getter, state=state, sleep=sleep, interval=interval,
                 now=now, stop=lambda: bool(state.get('stop')))
        except Exception as e:  # noqa: BLE001 — un instrumento roto no detiene la corrida
            state['failed'] += 1
            if len(state['errors']) < 20:
                state['errors'].append(f'{sym}: {type(e).__name__}')
        state['done'] += 1
        if state['consecutive_fail'] >= SOURCE_DOWN_AFTER:
            state['stopped_reason'] = 'source_down'
            break
    state['current'] = None
    return state


# ── fotos diarias ────────────────────────────────────────────────────────────
def _last_close(session, instrument_id, on):
    from sqlalchemy import text
    # solo un cierre RECIENTE (≤ SNAPSHOT_MAX_AGE_DAYS): una empresa deslistada o una serie que dejó de bajarse no
    # puede quedar en la foto de HOY con un cierre de hace meses (las fotos son append-only: quedaría para siempre)
    r = session.execute(text('SELECT close, currency, date FROM prices_eod WHERE instrument_id = :i AND source = :s '
                             'AND date <= :d AND date >= :lo ORDER BY date DESC LIMIT 1'),
                        {'i': instrument_id, 's': SOURCE, 'd': on,
                         'lo': on - timedelta(days=SNAPSHOT_MAX_AGE_DAYS)}).first()
    return (float(r[0]), r[1], r[2]) if r and r[0] is not None else (None, None, None)


def _fx_on(session, ccy, on, cache):
    from sqlalchemy import text

    from core.instruments import major_ccy
    maj, mult = major_ccy(ccy)
    if maj == 'USD':
        return mult
    if maj not in cache:
        r = session.execute(text('SELECT rate_to_usd FROM fx_daily WHERE ccy = :c AND source = :s AND date <= :d '
                                 'AND date >= :lo ORDER BY date DESC LIMIT 1'),
                            {'c': maj, 's': SOURCE, 'd': on, 'lo': on - timedelta(days=SNAPSHOT_MAX_AGE_DAYS)}).first()
        cache[maj] = float(r[0]) if r else None
    return cache[maj] * mult if cache[maj] else None


def _positions_rows(session, run_date, nodes_by_id, broker=True):
    """Filas de positions_eod: eco_pos / kh_portfolios de cada dueño + cuentas de corretaje."""
    from sqlalchemy import text
    rows = []
    try:
        st = session.execute(text("SELECT owner_hash, key, value FROM user_state WHERE key IN ('eco_pos', 'kh_portfolios')")).all()
    except Exception:  # noqa: BLE001
        st = []
    for owner, key, val in st:
        if key == 'eco_pos' and isinstance(val, dict):
            for nid, p in val.items():
                sym = (nodes_by_id.get(nid) or {}).get('mkt')
                qty = _f((p or {}).get('sh')) if isinstance(p, dict) else None
                if sym and qty:
                    rows.append((owner, 'market', str(sym).upper(), qty, 'user_state:eco_pos'))
        elif key == 'kh_portfolios' and isinstance(val, list):
            for pf in val:
                if not isinstance(pf, dict):
                    continue
                for p in pf.get('positions') or []:
                    sym = (nodes_by_id.get((p or {}).get('nodeId')) or {}).get('mkt')
                    qty = _f((p or {}).get('shares'))
                    if sym and qty:
                        rows.append((owner, f"pf:{pf.get('id')}"[:80], str(sym).upper(), qty, 'user_state:kh_portfolios'))
    if broker:
        try:
            from brokerage import service as bsvc
            for c in bsvc.list_clients(session):
                snap = bsvc.account_snapshot(session, c['id'])
                for p in (snap or {}).get('positions') or []:
                    qty = _f(p.get('qty'))
                    if p.get('symbol') and qty:
                        rows.append((f"broker:{c['id']}"[:64], 'alpaca', str(p['symbol']).upper().replace('/', ''),
                                     qty if (p.get('side') or 'long') != 'short' else -abs(qty), 'alpaca'))
        except Exception as e:  # noqa: BLE001 — sin corretaje configurado / Alpaca caído: solo lo del usuario
            log.info('positions_eod: corretaje no leído (%s)', type(e).__name__)
    return rows


def snapshot_daily(session, run_date=None, broker=True):
    """metrics_eod + positions_eod del día (una fila por clave; repetir es un no-op). → {metrics, positions}."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from ontology.history_models import MetricsEOD, PositionEOD
    run_date = _d(run_date or _now().date())
    fx_cache = {}
    try:
        from core import world
        g = world._graph()
        nodes, gen = g.get('nodes') or [], g.get('generation')
    except Exception:  # noqa: BLE001
        nodes, gen = [], None
    try:
        from core.live_caps import get_caps
        caps = get_caps(start=False).get('caps') or {}
    except Exception:  # noqa: BLE001
        caps = {}
    mrows = []
    for n in nodes:
        sym = n.get('ticker')
        close = cur = None
        if sym:
            close, cur, _dd = _last_close(session, str(sym).upper(), run_date)
        rate = _fx_on(session, cur, run_date, fx_cache) if close is not None else None
        cap = caps.get(n['id']) or {}
        mrows.append({'entity_id': str(n['id'])[:120], 'date': run_date, 'nrs': n.get('nrs'),
                      'flow_degree': n.get('flow_degree'), 'instrument_id': (str(sym).upper()[:32] if sym else None),
                      'close': close, 'currency': cur, 'price_usd': (close * rate) if (close and rate) else None,
                      'mcap_usd_b': _f(cap.get('mcap_b')), 'graph_generation': str(gen)[:64] if gen else None,
                      'source': {'nrs': 'core.world (fórmula única)', 'price': 'prices_eod' if close else None,
                                 'mcap': 'live_caps' if cap.get('mcap_b') is not None else None}})
    nm = 0
    for i in range(0, len(mrows), 500):
        res = session.execute(pg_insert(MetricsEOD.__table__).values(mrows[i:i + 500]).on_conflict_do_nothing()
                              .returning(MetricsEOD.__table__.c.entity_id))
        nm += len(res.fetchall())
    try:
        from core.instruments import catalog_nodes
        by_id = {n.get('id'): n for n in catalog_nodes()}
    except Exception:  # noqa: BLE001
        by_id = {}
    agg = {}
    for owner, pf, sym, qty, src in _positions_rows(session, run_date, by_id, broker=broker):
        k = (owner[:64], pf, sym[:32])
        q0, _s = agg.get(k, (0.0, src))
        agg[k] = (q0 + qty, src)
    prow = []
    for (owner, pf, sym), (qty, src) in agg.items():
        close, cur, _dd = _last_close(session, sym, run_date)
        rate = _fx_on(session, cur, run_date, fx_cache) if close is not None else None
        px_usd = close * rate if (close and rate) else None
        prow.append({'owner_hash': owner, 'portfolio': pf, 'instrument_id': sym, 'date': run_date, 'qty': qty,
                     'price': close, 'currency': cur, 'price_usd': px_usd,
                     'value_usd': qty * px_usd if px_usd else None, 'source': src})
    npos = 0
    for i in range(0, len(prow), 500):
        res = session.execute(pg_insert(PositionEOD.__table__).values(prow[i:i + 500]).on_conflict_do_nothing()
                              .returning(PositionEOD.__table__.c.owner_hash))
        npos += len(res.fetchall())
    return {'metrics': nm, 'positions': npos}


# ── trabajo DIARIO (core/scheduler) ──────────────────────────────────────────
_DAILY = {'running': False, 'last_day': None, 'last_started': None, 'last_finished': None, 'last_result': None,
          'paused_until': None, 'thread': None}
_DLOCK = threading.Lock()


def _daily_due(now):
    if now.weekday() >= 5 or now.hour < EOD_HOUR_UTC:
        return False, 'not_yet'
    if _DAILY['last_day'] == now.date().isoformat():
        return False, 'done_today'
    if _DAILY['paused_until'] and now.timestamp() < _DAILY['paused_until']:
        return False, 'source_paused'
    try:     # tras un reinicio: si la foto del día ya existe, el día está hecho (no se re-bajan ~600 series)
        from sqlalchemy import text

        from ontology.db import session_scope
        with session_scope() as s:
            if s.execute(text('SELECT 1 FROM metrics_eod WHERE date = :d LIMIT 1'), {'d': now.date()}).first():
                _DAILY['last_day'] = now.date().isoformat()
                return False, 'done_today'
    except Exception:  # noqa: BLE001
        return False, 'db_unavailable'
    return True, None


def run_daily(now=None, getter=None, sleep=time.sleep, broker=True):
    """Ingesta diaria (1 mes por instrumento, para detectar ajustes) + fotos del día. Bloqueante."""
    now = now or _now()
    state = {'stop': False}
    _DAILY.update(running=True, last_started=now.isoformat())
    try:
        _run(state, rng='1mo', getter=getter, sleep=sleep, now=now)
        snap = None
        if state.get('stopped_reason') != 'source_down':
            from ontology.db import session_scope
            with session_scope() as s:
                snap = snapshot_daily(s, now.date(), broker=broker)
            _DAILY['last_day'] = now.date().isoformat()
        else:
            _DAILY['paused_until'] = time.time() + SOURCE_PAUSE_S
        res = {k: state.get(k) for k in ('total', 'ok', 'failed', 'empty', 'rows', 'adjustments', 'repaired',
                                         'stopped_reason')}
        res['snapshot'] = snap
        res['errors'] = state.get('errors', [])[:5]
        _DAILY.update(last_result=res, last_finished=_now().isoformat())
        return res
    finally:
        _DAILY['running'] = False


def daily_tick(now=None, threaded=True):
    """Tarea del reloj: si toca, lanza la corrida del día en su propio hilo (no bloquea al reloj)."""
    if not daily_enabled():
        return {'skipped': 'disabled'}
    if not db_on():
        return {'skipped': 'no_database'}
    now = now or _now()
    with _DLOCK:
        if _DAILY['running'] or _BF['running']:
            return {'skipped': 'running'}
        ok, why = _daily_due(now)
        if not ok:
            return {'skipped': why}
        _DAILY['running'] = True
    if not threaded:
        return run_daily(now)

    def _go():
        try:
            from core import identity
            with identity.use(identity.system('prices_eod_daily')):
                run_daily()
        except Exception as e:  # noqa: BLE001
            _DAILY.update(running=False, last_result={'error': type(e).__name__})
            log.warning('prices_eod diario: %s', type(e).__name__)
    t = threading.Thread(target=_go, name='prices-eod-daily', daemon=True)
    _DAILY['thread'] = t
    t.start()
    return {'started': True}


# ── RELLENO de 5 años: SOLO a pedido del operador (PIN) ──────────────────────
_BF = {'running': False, 'stop': False, 'started_at': None, 'finished_at': None, 'years': None, 'symbols': None,
       'decision_id': None, 'by': None, 'total': 0, 'done': 0, 'ok': 0, 'skipped': 0, 'failed': 0, 'empty': 0,
       'rows': 0, 'adjustments': 0, 'current': None, 'errors': [], 'stopped_reason': None, 'consecutive_fail': 0}
_BLOCK = threading.Lock()


def backfill_state():
    st = {k: v for k, v in _BF.items() if k != 'stop'}
    st['errors'] = list(_BF.get('errors') or [])[:20]
    if _BF['running'] and _BF['started_at'] and _BF['done']:
        el = (_now() - datetime.fromisoformat(_BF['started_at'])).total_seconds()
        st['eta_s'] = int(el / _BF['done'] * max(0, _BF['total'] - _BF['done']))
    st['pct'] = round(100.0 * _BF['done'] / _BF['total'], 1) if _BF['total'] else 0.0
    return st


def start_backfill(principal, years=MAX_YEARS, symbols=None, getter=None, sleep=time.sleep, threaded=True,
                   interval=None):
    """Arranca el relleno (decisión 'data.backfill' por el operador). RuntimeError si ya corre."""
    from core import decisions
    from ontology.db import session_scope
    years = max(1, min(MAX_YEARS, int(years or MAX_YEARS)))
    symbols = [str(x).upper()[:32] for x in (symbols or []) if str(x).strip()][:200] or None
    with _BLOCK:
        if _BF['running'] or _DAILY['running']:
            raise RuntimeError('already_running')
        _BF.update(running=True, stop=False, started_at=_now().isoformat(), finished_at=None, years=years,
                   symbols=symbols, by=getattr(principal, 'id', None), total=0, done=0, errors=[],
                   stopped_reason=None)
    try:
        with session_scope() as s:
            eq, fx = _targets(s, symbols)
            with decisions.decision_scope('data.backfill', principal, session=s, durability='sync',
                                          subject={'action': 'start', 'years': years,
                                                   'instruments': len(eq), 'fx_pairs': len(fx)}) as ctx:
                ctx.params(years=years, symbols=symbols, source=SOURCE,
                           req_interval_s=req_interval_s() if interval is None else interval)
                ctx.output = {'targets': len(eq) + len(fx), 'source': SOURCE, 'years': years,
                              'resumable': True, 'note': 'BRECHAS #3: relleno a pedido del operador'}
            _BF['decision_id'] = str(ctx.id)
    except Exception:
        _BF['running'] = False
        raise

    def _go():
        try:
            _run(_BF, years=years, symbols=symbols, getter=getter, sleep=sleep, interval=(
                max(1.0, req_interval_s()) if interval is None else interval))
        except Exception as e:  # noqa: BLE001
            _BF['stopped_reason'] = f'error:{type(e).__name__}'
            log.warning('prices backfill: %s', type(e).__name__)
        finally:
            _BF.update(running=False, finished_at=_now().isoformat())
            _record_finish()
    if threaded:
        threading.Thread(target=_go, name='prices-backfill', daemon=True).start()
    else:
        _go()
    return backfill_state()


def _record_finish():
    """Decisión de cierre (hija de la de inicio), a nombre del reloj: cuánto se bajó y por qué terminó."""
    try:
        from core import decisions, identity
        from ontology.db import session_scope
        with session_scope() as s:
            with decisions.decision_scope('data.backfill', identity.system('prices_backfill'), session=s,
                                          durability='sync', parent_id=_BF.get('decision_id'),
                                          subject={'action': 'finish'}) as ctx:
                ctx.output = {k: _BF.get(k) for k in ('total', 'done', 'ok', 'skipped', 'failed', 'empty', 'rows',
                                                       'adjustments', 'stopped_reason')}
                ctx.output['errors'] = list(_BF.get('errors') or [])[:5]
    except Exception as e:  # noqa: BLE001
        log.warning('prices backfill: cierre no registrado (%s)', type(e).__name__)


def stop_backfill(principal):
    """Pide detener el relleno (se puede reanudar: lo ya bajado se salta). Deja su decisión."""
    from core import decisions
    from ontology.db import session_scope
    if not _BF['running']:
        return False
    with session_scope() as s:
        with decisions.decision_scope('data.backfill', principal, session=s, durability='sync',
                                      parent_id=_BF.get('decision_id'), subject={'action': 'stop'}) as ctx:
            ctx.output = {'done': _BF['done'], 'total': _BF['total']}
    _BF['stop'] = True
    return True


def _reset_for_tests():
    _READ_PAUSE.update(until=0.0, error=None)
    _BF.update(running=False, stop=False, started_at=None, finished_at=None, decision_id=None, total=0, done=0,
               errors=[], stopped_reason=None)
    _DAILY.update(running=False, last_day=None, last_result=None, paused_until=None, thread=None)
