"""core/ai_usage.py — CONTROL DE GASTO DE IA (registro, límites y reporte).

Pedido (2026-10-02, Fabrizio): "quisiera saber el saldo del API… controlar el
gasto, y de dónde está gastando en cada caso porque hay más de una IA
conectada; ahora no sé cuánto estoy gastando en probar".

· REGISTRO: cada llamada a un proveedor (Claude, Gemini, NVIDIA) anota
  proveedor, modelo, tokens de entrada/salida (los que DEVUELVE el proveedor;
  si no los da, estimados y rotulados), costo estimado, la FUNCIÓN de la app que
  la pidió (chat de Khipu, comité, investigación, canvas…) y QUIÉN (usuario o
  cliente). En memoria al instante y en Postgres (tabla ai_usage) en lotes.
· LÍMITES: tope diario y mensual global, por función y por usuario/cliente
  (editables con PIN desde 🩺 Sistema → 💰 Gasto IA; valores por defecto en env).
  Al llegar al tope la llamada se RECHAZA con un mensaje claro (nunca cobra).
· SALDO: ningún proveedor publica el "saldo restante" por API. Lo más cercano:
  si se configura ANTHROPIC_ADMIN_KEY (llave Admin sk-ant-admin…, solo
  organizaciones), se lee el reporte de costos REAL de Anthropic del mes.

Precios por 1M tokens (entrada, salida) — ESTIMACIÓN; se pueden ajustar con
AI_PRICES_JSON='{"claude-sonnet-5": [2, 10], ...}'.
"""
import json
import logging
import os
import threading
import time
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

log = logging.getLogger('khipu')

PRICES = {   # prefijo de modelo → (USD por 1M tokens de entrada, de salida)
    'claude-fable-5': (10.0, 50.0), 'claude-opus-5-5': (4.0, 20.0), 'claude-opus-5': (5.0, 25.0),
    'claude-opus-4': (5.0, 25.0), 'claude-sonnet-5-5': (2.0, 10.0), 'claude-sonnet-5': (2.0, 10.0),
    'claude-sonnet-4': (3.0, 15.0), 'claude-haiku-4': (1.0, 5.0), 'claude': (3.0, 15.0),
    'gemini:gemini-2.5-pro': (1.25, 10.0), 'gemini:gemini-3-pro': (2.0, 12.0), 'gemini:gemini-2.5-flash-lite': (0.1, 0.4),
    'gemini:gemini-2.5-flash': (0.3, 2.5), 'gemini': (0.3, 2.5),
    'nvidia': (0.0, 0.0),        # catálogo de NVIDIA: gratis con créditos de desarrollador
}

FEATURE_BY_PATH = (
    ('/api/khipu/chat', 'khipu_chat'), ('/api/bixby', 'voz'), ('/api/voice', 'voz'),
    ('/api/canvas', 'canvas'), ('/api/sim/agents', 'simulacion_agentes'), ('/api/committee', 'comite'),
    ('/api/research/deep', 'investigacion_profunda'), ('/api/research', 'investigacion'),
    ('/api/portfolio-ai', 'asistente_carteras'), ('/api/portfolio', 'riesgo_cartera'),
    ('/api/world', 'world_monitor'), ('/api/space', 'espacio'), ('/api/ai/command', 'comandos'),
    ('/api/ai/analyze', 'analisis_ia'), ('/api/ai', 'analisis_ia'), ('/api/ontology/agents', 'agentes_ontologia'),
    ('/api/ontology', 'ontologia'), ('/api/matrix', 'insights_matriz'), ('/api/news', 'noticias'),
    ('/api/diagnostics', 'diagnostico'), ('/api/health', 'diagnostico'), ('/mcp', 'mcp'), ('/v1/', 'api_v1'),
    ('/api/trade', 'trading'), ('/api/brokerage', 'clientes'),
)
FEATURE_LABELS = {
    'khipu_chat': ('Chat de Khipu', 'Khipu chat'), 'voz': ('Voz de Khipu', 'Khipu voice'),
    'canvas': ('Canvas IA', 'AI Canvas'), 'simulacion_agentes': ('Simulación por agentes', 'Agent simulation'),
    'comite': ('Comité de inversión', 'Investment committee'), 'investigacion': ('Investigación IA', 'AI research'),
    'investigacion_profunda': ('Investigación profunda', 'Deep research'),
    'asistente_carteras': ('Asistente de carteras', 'Portfolio assistant'), 'riesgo_cartera': ('Riesgo de cartera', 'Portfolio risk'),
    'world_monitor': ('World Monitor', 'World Monitor'), 'espacio': ('Space Monitor', 'Space Monitor'),
    'comandos': ('Comandos', 'Commands'), 'analisis_ia': ('Análisis IA (varios)', 'AI analysis (misc)'),
    'agentes_ontologia': ('Agentes de la ontología', 'Ontology agents'), 'ontologia': ('Ontología', 'Ontology'),
    'insights_matriz': ('Insights', 'Insights'), 'noticias': ('Noticias', 'News'), 'diagnostico': ('Diagnóstico 🩺', 'Diagnostics 🩺'),
    'mcp': ('IAs externas (MCP)', 'External AIs (MCP)'), 'api_v1': ('API pública /v1', 'Public API /v1'),
    'trading': ('Agente de trading', 'Trading agent'), 'clientes': ('Clientes', 'Clients'),
    'fondo': ('Tareas de fondo', 'Background tasks'), 'otro': ('Otro', 'Other'),
}

_TLS = threading.local()
_LOCK = threading.Lock()
_RECENT = deque(maxlen=400)       # últimas llamadas (para la pantalla)
_DAY = {}                         # 'YYYY-MM-DD' → {(provider, model, feature, who): [calls, tin, tout, cost]}
_QUEUE = []                       # filas pendientes de escribir en Postgres
_STATE = {'loaded': False, 'writer': None, 'settings': None, 'settings_at': 0.0, 'admin': None, 'admin_at': 0.0}


class AIBudgetError(RuntimeError):
    """Se alcanzó un límite de gasto: la llamada NO se hace (no cobra)."""

    def __init__(self, es, en, scope=None):
        super().__init__(f'{es} / {en}')
        self.es, self.en, self.scope = es, en, scope


def _now():
    return datetime.now(timezone.utc)


def _today():
    return _now().date().isoformat()


def _prices():
    p = dict(PRICES)
    try:
        extra = json.loads(os.getenv('AI_PRICES_JSON', '') or '{}')
        for k, v in extra.items():
            p[str(k)] = (float(v[0]), float(v[1]))
    except Exception:  # noqa: BLE001
        pass
    return p


def price_for(provider, model):
    """(entrada, salida) USD por 1M tokens. Prefijo más largo que calce."""
    m = str(model or provider or '').lower()
    if provider in ('gemini', 'nvidia') and not m.startswith(provider):
        m = f'{provider}:{m}'
    best = None
    for k, v in _prices().items():
        if m.startswith(k) and (best is None or len(k) > len(best[0])):
            best = (k, v)
    if best:
        return best[1]
    return _prices().get(provider, (3.0, 15.0))


def cost_of(provider, model, tin, tout):
    pin, pout = price_for(provider, model)
    return round((tin or 0) * pin / 1e6 + (tout or 0) * pout / 1e6, 6)


# ── contexto: qué función y quién ───────────────────────────────────────────
@contextmanager
def ai_context(feature=None, who=None):
    prev = (getattr(_TLS, 'feature', None), getattr(_TLS, 'who', None))
    if feature:
        _TLS.feature = feature
    if who:
        _TLS.who = str(who)[:120]
    try:
        yield
    finally:
        _TLS.feature, _TLS.who = prev


def current():
    f, w = getattr(_TLS, 'feature', None), getattr(_TLS, 'who', None)
    if f and w:
        return {'feature': f, 'who': w}
    try:
        from flask import has_request_context, request
        if has_request_context():
            p = request.path or ''
            f = f or next((feat for pre, feat in FEATURE_BY_PATH if p.startswith(pre)), 'otro')
            if not w:
                w = request.headers.get('X-Khipu-Actor') or ''
                if not w and request.is_json:
                    body = request.get_json(silent=True) or {}
                    w = body.get('actor') if isinstance(body, dict) else ''
                w = (str(w).strip()[:120] or ('mcp' if f == 'mcp' else 'api_v1' if f == 'api_v1' else 'app'))
    except Exception:  # noqa: BLE001
        pass
    return {'feature': f or 'fondo', 'who': w or 'sistema'}


def bind(fn):
    """Envuelve fn para que, al correr en OTRO hilo (ThreadPoolExecutor), herede
    la función/quién del hilo que la creó."""
    ctx = current()

    def wrapper(*a, **k):
        with ai_context(**ctx):
            return fn(*a, **k)
    return wrapper


# ── ajustes (límites) ───────────────────────────────────────────────────────
def _env_float(name, default):
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return float(default)


def default_settings():
    return {'daily_usd': _env_float('AI_DAILY_LIMIT_USD', 10.0),
            'monthly_usd': _env_float('AI_MONTHLY_LIMIT_USD', 150.0),
            'per_who_daily_usd': _env_float('AI_PER_USER_DAILY_USD', 0.0),     # 0 = sin tope por persona
            'per_feature_daily_usd': {}, 'blocked_providers': [], 'warn_pct': 80}


def settings():
    if _STATE['settings'] is not None and time.time() - _STATE['settings_at'] < 60:
        return _STATE['settings']
    s = default_settings()
    try:
        from ontology.db import ontology_available, session_scope
        if ontology_available():
            from research.models import AISetting
            with session_scope() as db:
                row = db.get(AISetting, 'limits')
                if row and isinstance(row.value, dict):
                    s.update({k: v for k, v in row.value.items() if k in s})
    except Exception:  # noqa: BLE001 — sin base: valores del entorno
        pass
    _STATE['settings'], _STATE['settings_at'] = s, time.time()
    return s


def save_settings(values, actor):
    s = default_settings()
    s.update(settings())
    for k in ('daily_usd', 'monthly_usd', 'per_who_daily_usd', 'warn_pct'):
        if k in values:
            s[k] = max(0.0, float(values[k]))
    if isinstance(values.get('per_feature_daily_usd'), dict):
        s['per_feature_daily_usd'] = {str(k)[:40]: max(0.0, float(v)) for k, v in values['per_feature_daily_usd'].items()
                                      if v not in (None, '')}
    if isinstance(values.get('blocked_providers'), list):
        s['blocked_providers'] = [p for p in values['blocked_providers'] if p in ('claude', 'gemini', 'nvidia')]
    from ontology.db import session_scope
    from research.models import AISetting
    with session_scope() as db:
        row = db.get(AISetting, 'limits')
        if row is None:
            row = AISetting(key='limits')
            db.add(row)
        row.value, row.updated_by, row.updated_at = s, str(actor)[:120], _now()
    _STATE['settings'], _STATE['settings_at'] = s, time.time()
    return s


# ── totales en memoria (rápidos, para los límites) ──────────────────────────
def _add(day, key, tin, tout, cost, n=1):
    d = _DAY.setdefault(day, {})
    a = d.setdefault(key, [0, 0, 0, 0.0])
    a[0] += n
    a[1] += tin
    a[2] += tout
    a[3] += cost


def _load_from_db():
    """Al primer uso: trae del registro persistente lo gastado este mes (un
    reinicio del servidor no debe poner los límites en cero)."""
    if _STATE['loaded']:
        return
    _STATE['loaded'] = True
    try:
        from ontology.db import ontology_available, session_scope
        if not ontology_available():
            return
        from sqlalchemy import func

        from research.models import AIUsage
        since = _now().replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=31)
        with session_scope() as db:
            rows = (db.query(func.date(AIUsage.at), AIUsage.provider, AIUsage.model, AIUsage.feature, AIUsage.who,
                             func.count(), func.sum(AIUsage.tokens_in), func.sum(AIUsage.tokens_out),
                             func.sum(AIUsage.cost_usd))
                    .filter(AIUsage.at >= since)
                    .group_by(func.date(AIUsage.at), AIUsage.provider, AIUsage.model, AIUsage.feature, AIUsage.who)
                    .all())
        with _LOCK:
            for day, prov, model, feat, who, n, tin, tout, cost in rows:
                _add(str(day), (prov, model, feat, who), int(tin or 0), int(tout or 0), float(cost or 0), n=int(n))
    except Exception as e:  # noqa: BLE001
        log.warning('ai_usage: no pude leer el historial (%s)', type(e).__name__)


def _spent(day=None, month=None, feature=None, who=None):
    tot = 0.0
    for d, rows in _DAY.items():
        if day and d != day:
            continue
        if month and not d.startswith(month):
            continue
        for (_p, _m, f, w), a in rows.items():
            if feature and f != feature:
                continue
            if who and w != who:
                continue
            tot += a[3]
    return tot


def check(provider, max_tokens=None):
    """Antes de cada llamada: ¿se pasó algún límite? → AIBudgetError (no se llama)."""
    try:
        if max_tokens is not None and int(max_tokens) <= 4:
            return                               # ping del 🩺: no cuenta
    except (TypeError, ValueError):
        pass
    _load_from_db()
    s = settings()
    ctx = current()
    if provider in (s.get('blocked_providers') or []):
        raise AIBudgetError(f'{provider} está desactivado en 🩺 Sistema → 💰 Gasto IA',
                            f'{provider} is disabled in 🩺 System → 💰 AI spend', 'provider')
    today, month = _today(), _today()[:7]
    with _LOCK:
        day_spent = _spent(day=today)
        month_spent = _spent(month=month)
        feat_spent = _spent(day=today, feature=ctx['feature'])
        who_spent = _spent(day=today, who=ctx['who'])
    if s.get('daily_usd') and day_spent >= s['daily_usd']:
        raise AIBudgetError(f"Se alcanzó el límite diario de gasto de IA (${s['daily_usd']:.2f}). Súbelo en 🩺 Sistema → 💰 Gasto IA o espera a mañana.",
                            f"Daily AI spend limit reached (${s['daily_usd']:.2f}). Raise it in 🩺 System → 💰 AI spend or wait until tomorrow.", 'daily')
    if s.get('monthly_usd') and month_spent >= s['monthly_usd']:
        raise AIBudgetError(f"Se alcanzó el límite mensual de gasto de IA (${s['monthly_usd']:.2f}).",
                            f"Monthly AI spend limit reached (${s['monthly_usd']:.2f}).", 'monthly')
    lim = (s.get('per_feature_daily_usd') or {}).get(ctx['feature'])
    if lim and feat_spent >= float(lim):
        lab = FEATURE_LABELS.get(ctx['feature'], (ctx['feature'], ctx['feature']))
        raise AIBudgetError(f'«{lab[0]}» llegó a su límite diario de IA (${float(lim):.2f}).',
                            f'“{lab[1]}” reached its daily AI limit (${float(lim):.2f}).', 'feature')
    pw = s.get('per_who_daily_usd') or 0
    if pw and ctx['who'] not in ('sistema', 'app') and who_spent >= pw:
        raise AIBudgetError(f"{ctx['who']} llegó a su límite diario de IA (${pw:.2f}).",
                            f"{ctx['who']} reached their daily AI limit (${pw:.2f}).", 'who')


def record(provider, model, tin, tout, ok=True, ms=None, estimated=False):
    """Después de cada respuesta del proveedor (también las que se descartan:
    se cobraron igual)."""
    try:
        tin, tout = int(tin or 0), int(tout or 0)
        ctx = current()
        cost = cost_of(provider, model, tin, tout)
        row = {'at': _now(), 'provider': provider, 'model': str(model or '')[:80], 'feature': ctx['feature'],
               'who': ctx['who'], 'tokens_in': tin, 'tokens_out': tout, 'cost_usd': cost,
               'estimated': bool(estimated), 'ok': bool(ok), 'ms': int(ms) if ms else None}
        with _LOCK:
            _add(row['at'].date().isoformat(), (provider, row['model'], ctx['feature'], ctx['who']), tin, tout, cost)
            _RECENT.appendleft(dict(row, at=row['at'].isoformat()))
            _QUEUE.append(row)
        _ensure_writer()
    except Exception as e:  # noqa: BLE001 — el registro nunca rompe una llamada
        log.warning('ai_usage.record: %s', type(e).__name__)


def estimate_tokens(text):
    return max(1, len(text or '') // 4)


# ── escritura en lotes ───────────────────────────────────────────────────────
def flush():
    with _LOCK:
        rows, _QUEUE[:] = list(_QUEUE), []
    if not rows:
        return 0
    try:
        from ontology.db import ontology_available, session_scope
        if not ontology_available():
            return 0
        from research.models import AIUsage
        with session_scope() as db:
            db.bulk_insert_mappings(AIUsage, rows)
        return len(rows)
    except Exception as e:  # noqa: BLE001
        log.warning('ai_usage.flush: %s (%d filas en memoria)', type(e).__name__, len(rows))
        with _LOCK:
            if len(_QUEUE) < 5000:
                _QUEUE[:0] = rows
        return 0


def _ensure_writer():
    t = _STATE['writer']
    if t is not None and t.is_alive():
        return

    def loop():
        while True:
            time.sleep(15)
            flush()
    t = threading.Thread(target=loop, name='ai-usage-writer', daemon=True)
    _STATE['writer'] = t
    t.start()


# ── reporte ──────────────────────────────────────────────────────────────────
def _agg_db(days):
    from sqlalchemy import func

    from ontology.db import session_scope
    from research.models import AIUsage
    since = _now() - timedelta(days=days)
    with session_scope() as db:
        rows = (db.query(func.date(AIUsage.at), AIUsage.provider, AIUsage.model, AIUsage.feature, AIUsage.who,
                         func.count(), func.sum(AIUsage.tokens_in), func.sum(AIUsage.tokens_out), func.sum(AIUsage.cost_usd))
                .filter(AIUsage.at >= since)
                .group_by(func.date(AIUsage.at), AIUsage.provider, AIUsage.model, AIUsage.feature, AIUsage.who).all())
    return [(str(d), p, m, f, w, int(n), int(ti or 0), int(to or 0), float(c or 0)) for d, p, m, f, w, n, ti, to, c in rows]


def report(days=30, lang='es'):
    flush()
    _load_from_db()
    rows, source = None, 'memory'
    try:
        from ontology.db import ontology_available
        if ontology_available():
            rows, source = _agg_db(days), 'database'
    except Exception as e:  # noqa: BLE001
        log.warning('ai_usage.report db: %s', type(e).__name__)
    if rows is None:
        cut = (_now() - timedelta(days=days)).date().isoformat()
        with _LOCK:
            rows = [(d, p, m, f, w, a[0], a[1], a[2], a[3]) for d, rs in _DAY.items() if d >= cut
                    for (p, m, f, w), a in rs.items()]
    today, month = _today(), _today()[:7]
    week = (_now() - timedelta(days=6)).date().isoformat()

    def group(idx, only=None):
        out = {}
        for r in rows:
            if only and not only(r):
                continue
            k = r[idx]
            a = out.setdefault(k, {'key': k, 'calls': 0, 'tokens_in': 0, 'tokens_out': 0, 'cost_usd': 0.0})
            a['calls'] += r[5]
            a['tokens_in'] += r[6]
            a['tokens_out'] += r[7]
            a['cost_usd'] += r[8]
        return sorted(({**v, 'cost_usd': round(v['cost_usd'], 4)} for v in out.values()), key=lambda x: -x['cost_usd'])

    def total(pred):
        return round(sum(r[8] for r in rows if pred(r)), 4)
    es = not str(lang).startswith('en')
    feats = group(3)
    for f in feats:
        lab = FEATURE_LABELS.get(f['key'], (f['key'], f['key']))
        f['label'] = lab[0] if es else lab[1]
    s = settings()
    spent_today, spent_month = total(lambda r: r[0] == today), total(lambda r: r[0].startswith(month))
    with _LOCK:
        recent = list(_RECENT)[:60]
    for r in recent:
        lab = FEATURE_LABELS.get(r['feature'], (r['feature'], r['feature']))
        r['feature_label'] = lab[0] if es else lab[1]
    return {
        'source': source, 'days': days,
        'totals': {'today': spent_today, 'week': total(lambda r: r[0] >= week), 'month': spent_month,
                   'period': total(lambda r: True), 'calls_today': sum(r[5] for r in rows if r[0] == today)},
        'by_provider': group(1), 'by_model': group(2), 'by_feature': feats, 'by_who': group(4),
        'by_day': sorted(group(0), key=lambda x: x['key']),
        'today_by_provider': group(1, lambda r: r[0] == today),
        'limits': s, 'remaining': {
            'today': round(max(0.0, s['daily_usd'] - spent_today), 4) if s.get('daily_usd') else None,
            'month': round(max(0.0, s['monthly_usd'] - spent_month), 4) if s.get('monthly_usd') else None},
        'prices': {k: list(v) for k, v in _prices().items()},
        'recent': recent, 'anthropic_billed': anthropic_cost_report(),
        'note_es': ('Costos ESTIMADOS con los tokens que devuelve cada proveedor y los precios de lista. '
                    'Ningún proveedor publica el saldo restante por API: revísalo en su consola.'),
        'note_en': ('ESTIMATED costs from the tokens each provider returns and list prices. '
                    'No provider exposes the remaining balance via API: check it in their console.'),
    }


def anthropic_cost_report():
    """Costo REAL facturado por Anthropic este mes (Usage & Cost Admin API).
    Requiere ANTHROPIC_ADMIN_KEY (sk-ant-admin…, solo organizaciones). Caché 10 min."""
    key = os.getenv('ANTHROPIC_ADMIN_KEY', '').strip()
    if not key:
        return {'available': False, 'reason': 'no_admin_key'}
    if _STATE['admin'] is not None and time.time() - _STATE['admin_at'] < 600:
        return _STATE['admin']
    out = {'available': False}
    try:
        import requests
        start = _now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        params = {'starting_at': start.strftime('%Y-%m-%dT%H:%M:%SZ'), 'limit': 31}
        headers = {'x-api-key': key, 'anthropic-version': '2023-06-01'}
        total_cents, pages, page = 0.0, 0, None
        while pages < 5:
            if page:
                params['page'] = page
            r = requests.get('https://api.anthropic.com/v1/organizations/cost_report', params=params,
                             headers=headers, timeout=15)
            if not r.ok:
                out = {'available': False, 'reason': f'HTTP {r.status_code}'}
                break
            d = r.json() or {}
            for bucket in d.get('data') or []:
                for res in bucket.get('results') or []:
                    try:
                        total_cents += float(res.get('amount') or 0)    # decimal en CENTAVOS de USD
                    except (TypeError, ValueError):
                        pass
            pages += 1
            page = d.get('next_page')
            if not d.get('has_more') or not page:
                out = {'available': True, 'month_usd': round(total_cents / 100.0, 2),
                       'since': params['starting_at'], 'source': 'Anthropic Usage & Cost Admin API'}
                break
    except Exception as e:  # noqa: BLE001
        out = {'available': False, 'reason': type(e).__name__}
    _STATE['admin'], _STATE['admin_at'] = out, time.time()
    return out


def _reset_for_tests():
    with _LOCK:
        _RECENT.clear()
        _DAY.clear()
        _QUEUE.clear()
    _STATE.update({'loaded': False, 'settings': None, 'settings_at': 0.0, 'admin': None, 'admin_at': 0.0})
