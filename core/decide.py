"""core/decide.py — JEV (TypeSafe AI, modelo "System One"): DECISIONES, no texto.

Pedido de Fabrizio (2026-10-04): usar Jev como "optimizador de costos, revisor
y primera capa de decisión". Jev no redacta: recibe un ESTADO + PREGUNTAS
tipadas y devuelve respuestas que el código usa directo, con probabilidades
CALIBRADAS y confianza:
  · choice → elige una opción (choice, probabilities, confidence)
  · score  → nivel en una rúbrica (score, legend, probabilities, confidence)
  · noul   → ¿es verdad? (noul 0-1)
Todas las preguntas de una llamada se evalúan en paralelo (sumar preguntas
casi no cambia tiempo ni costo) → se piden TODAS las que el código pueda
necesitar y se combinan en código (patrón "speculative fan-out").

API: POST https://api.typesafe.ai/v1/systemone · Authorization: Bearer
TYPESAFE_API_KEY · body {state, model:'jev-latest', questions:{id:{type,
instructions,criteria?}}} → {model, answers:{id:{...}}, usage:{input_tokens,
output_tokens}}. Revisado 2026-10-10 contra lo publicado (guías de Apidog/LiteLLM/
Netlify AI Gateway; docs.typesafe.ai/api no se pudo abrir desde aquí): mismo
endpoint, mismos 3 campos (state/model/questions), respuestas answers.<id>.choice /
.score / .noul con probabilities + confidence (+ legend en score); jev-latest ≈
jev-1.13.0; estado + preguntas ≈ 32K tokens máx.; 70-500 ms.

REGLAS DE LA CASA
· ÚNICA puerta a TypeSafe (como core/ai.py lo es para Claude/Gemini/NVIDIA).
· Cada llamada se registra en 💰 Gasto IA (core/ai_usage: proveedor 'typesafe')
  y respeta sus límites. Precio: desconocido al integrar → 0 hasta fijar
  AI_PRICES_JSON='{"typesafe:jev": [x, y]}' (se rotula "estimado").
· MODO SOMBRA (DECIDE_SHADOW=on por defecto): cada decisión se guarda junto a
  lo que el sistema hizo de verdad (tabla decision_shadow + memoria) para medir
  acuerdo. CONTROL (2026-10-10, Fabrizio pagó TypeSafe): con clave y
  DECIDE_CONTROL sin poner, Jev MANDA en el chat ('chat_gate'); DECIDE_CONTROL=off
  lo deja solo en sombra; una lista explícita ('chat_gate,news', 'all') sigue valiendo.
· Nunca rompe nada: sin clave, sin red o con error → None y el sistema sigue
  igual que hoy. NUNCA decide dinero.

API interna:
  available() · ask(state, questions, feature=None, timeout=) → answers|None ·
  chat_gate_start(message, lang) → future · chat_gate_finish(fut, out) ·
  shadow(feature, key, decision, actual, agree) · shadow_report(days)
"""
import json
import logging
import os
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

from core import ai_usage

log = logging.getLogger('khipu')

API_URL = os.getenv('TYPESAFE_API_URL') or 'https://api.typesafe.ai/v1/systemone'
MODEL = os.getenv('TYPESAFE_MODEL') or 'jev-latest'
PROVIDER = 'typesafe'
TIMEOUT_S = float(os.getenv('DECIDE_TIMEOUT_S') or 6.0)
# Jev AL MANDO del chat (DECIDE_CONTROL incluye 'chat_gate'): cuánto más se le espera después de la
# pre-consulta (ya corre en paralelo desde que llega la pregunta) y la confianza mínima para obedecerle.
CONTROL_WAIT_S = float(os.getenv('DECIDE_WAIT_S') or 1.5)
MIN_CONF = float(os.getenv('DECIDE_MIN_CONF') or 0.6)
MAX_STATE_CHARS = 12000

_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix='decide')
_LOCK = threading.Lock()
_RECENT = deque(maxlen=400)          # sombra en memoria (sin Postgres también sirve)
_STATS = {}                          # feature → {'n': int, 'agree': int}


def _key():
    return (os.getenv('TYPESAFE_API_KEY') or os.getenv('TYPESAFE_KEY') or '').strip()


def available():
    return bool(_key()) and (os.getenv('DECIDE_ENABLED') or 'on').lower() not in ('off', '0', 'false')


def shadow_mode():
    return (os.getenv('DECIDE_SHADOW') or 'on').lower() not in ('off', '0', 'false')


CONTROL_DEFAULT = ('chat_gate',)        # con clave y DECIDE_CONTROL sin poner: Jev manda en el chat
_CONTROL_OFF = ('off', 'none', '0', 'false', 'no')


def control_features():
    """Funciones donde Jev MANDA (2026-10-10, Fabrizio pagó TypeSafe):
    · DECIDE_CONTROL sin poner (o vacía) → ('chat_gate',): Jev decide la ruta del chat por defecto;
    · 'off' / 'none' / '0' / 'false' → ninguna (solo sombra);
    · lista explícita ('chat_gate,news' o 'all') → esa lista.
    Las reglas de seguridad no cambian: confianza mínima, nunca dinero, sin respuesta a tiempo → camino normal."""
    raw = (os.getenv('DECIDE_CONTROL') or '').strip()
    if not raw:
        return list(CONTROL_DEFAULT)
    if raw.lower() in _CONTROL_OFF:
        return []
    return [x.strip() for x in raw.split(',') if x.strip() and x.strip().lower() not in _CONTROL_OFF]


def control(feature):
    """¿Jev MANDA en esta función? Hace falta clave (available) y que la función esté en control_features()."""
    allowed = control_features()
    return available() and (feature in allowed or 'all' in allowed)


def _now():
    return datetime.now(timezone.utc)


def _trim_state(state):
    if isinstance(state, str):
        return state[:MAX_STATE_CHARS]
    try:
        s = json.dumps(state, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        return str(state)[:MAX_STATE_CHARS]
    return state if len(s) <= MAX_STATE_CHARS else s[:MAX_STATE_CHARS]


def ask(state, questions, feature=None, timeout=None):
    """Una llamada a Jev. Devuelve {id: answer} o None (sin clave/red/error).
    Las preguntas van tal cual el formato de TypeSafe (type/instructions/criteria)."""
    if not available() or not questions:
        return None
    ctx = ai_usage.ai_context(feature, None) if feature else None
    t0 = time.monotonic()
    try:
        if ctx:
            ctx.__enter__()
        try:
            ai_usage.check(PROVIDER)
        except ai_usage.AIBudgetError as e:
            log.info('decide: fuera de presupuesto (%s)', e.scope)
            return None
        body = {'state': _trim_state(state), 'model': MODEL, 'questions': questions}
        r = requests.post(API_URL, json=body, timeout=timeout or TIMEOUT_S,
                          headers={'Authorization': 'Bearer ' + _key(), 'Content-Type': 'application/json'})
        ms = int((time.monotonic() - t0) * 1000)
        if r.status_code != 200:
            ai_usage.record(PROVIDER, MODEL, 0, 0, ok=False, ms=ms)
            log.warning('decide: HTTP %s', r.status_code)
            return None
        d = r.json()
        u = d.get('usage') or {}
        ai_usage.record(PROVIDER, d.get('model') or MODEL, u.get('input_tokens', 0), u.get('output_tokens', 0),
                        ok=True, ms=ms, estimated=not u)
        ans = d.get('answers')
        return ans if isinstance(ans, dict) else None
    except Exception as e:  # noqa: BLE001 — Jev es opcional: nunca rompe al que pregunta
        log.warning('decide: %s', type(e).__name__)
        try:
            ai_usage.record(PROVIDER, MODEL, 0, 0, ok=False, ms=int((time.monotonic() - t0) * 1000))
        except Exception:  # noqa: BLE001
            pass
        return None
    finally:
        if ctx:
            try:
                ctx.__exit__(None, None, None)
            except Exception:  # noqa: BLE001
                pass


# ── sombra: lo que Jev decidió vs lo que pasó ────────────────────────────────
def shadow(feature, key, decision, actual, agree):
    row = {'at': _now(), 'feature': str(feature)[:40], 'key': str(key or '')[:200], 'decision': decision,
           'actual': actual, 'agree': None if agree is None else bool(agree)}
    with _LOCK:
        _RECENT.appendleft(row)
        st = _STATS.setdefault(row['feature'], {'n': 0, 'agree': 0})
        if agree is not None:
            st['n'] += 1
            st['agree'] += 1 if agree else 0
    _POOL.submit(_persist, row)


def _persist(row):
    try:
        from ontology.db import ontology_available as db_ok, session_scope
        if not db_ok():
            return
        from research.models import DecisionShadow
        with session_scope() as s:
            s.add(DecisionShadow(at=row['at'], feature=row['feature'], key=row['key'], decision=row['decision'],
                                 actual=row['actual'], agree=row['agree']))
    except Exception as e:  # noqa: BLE001
        log.info('decide: sombra no guardada (%s)', type(e).__name__)


def shadow_report(days=30, limit=50):
    """Acuerdo Jev ↔ sistema por función (Postgres si hay; si no, memoria)."""
    feats = {}
    try:
        from ontology.db import ontology_available as db_ok, session_scope
        from research.models import DecisionShadow
        if db_ok():
            since = _now() - timedelta(days=int(days))
            with session_scope() as s:
                for r in s.query(DecisionShadow).filter(DecisionShadow.at >= since):
                    f = feats.setdefault(r.feature, {'n': 0, 'agree': 0})
                    if r.agree is not None:
                        f['n'] += 1
                        f['agree'] += 1 if r.agree else 0
    except Exception:  # noqa: BLE001
        feats = {}
    if not feats:
        with _LOCK:
            feats = {k: dict(v) for k, v in _STATS.items()}
    out = []
    for k, v in feats.items():
        out.append({'feature': k, 'n': v['n'], 'agree': v['agree'],
                    'agree_pct': round(100.0 * v['agree'] / v['n'], 1) if v['n'] else None,
                    'control': control(k)})
    with _LOCK:
        recent = [dict(r, at=r['at'].isoformat()) for r in list(_RECENT)[:limit]]
    ctl = control_features() if available() else []
    if ctl:
        note_es = ('Jev MANDA en: ' + ', '.join(ctl) + ' (DECIDE_CONTROL; sin poner = chat_gate). Igual se compara '
                   'en sombra con lo que hizo el sistema. DECIDE_CONTROL=off lo deja solo en sombra.')
        note_en = ('Jev is IN CONTROL of: ' + ', '.join(ctl) + ' (DECIDE_CONTROL; unset = chat_gate). It is still '
                   'compared in shadow mode against what the system did. DECIDE_CONTROL=off keeps it shadow-only.')
    else:
        note_es = ('Jev decide en sombra: se compara con lo que hizo el sistema. Se le da control por función '
                   '(DECIDE_CONTROL) cuando el acuerdo lo merezca.')
        note_en = ('Jev decides in shadow mode: compared against what the system actually did. It gets control per '
                   'feature (DECIDE_CONTROL) once agreement earns it.')
    return {'available': available(), 'shadow': shadow_mode(), 'model': MODEL, 'features': out, 'recent': recent,
            'control_features': ctl, 'note_es': note_es, 'note_en': note_en}


# ── PORTERO DEL CHAT DE KHIPU (primer uso, en sombra) ───────────────────────
# Pregunta en una sola llamada todo lo que el enrutador podría necesitar.
CHAT_QUESTIONS = {
    'route': {
        'type': 'choice',
        'instructions': 'What does answering `message` require from a financial-terminal assistant that has live '
                        'company data, prices, supply-chain graph, news and research tools?',
        'criteria': {
            'local_fact': 'A single stored fact or number (a price, a company profile, a definition) with no reasoning',
            'needs_tools': 'Looking up one or two live data sources (news, prices, suppliers) and summarizing them',
            'needs_deep_reasoning': 'Multi-step analysis, comparing several things, a thesis, or an open-ended question',
            'offtopic': 'Small talk or something unrelated to investing, companies or markets',
        },
    },
    'mentions_company': {'type': 'noul', 'instructions': 'Does `message` refer to a specific company, ticker or asset?'},
    'asks_trade': {'type': 'noul', 'instructions': 'Does `message` ask to place, confirm or cancel a buy or sell order?'},
    'about_portfolio': {'type': 'noul', 'instructions': 'Is `message` about the user\'s own portfolio or positions?'},
    'urgency': {'type': 'score', 'instructions': 'How time-sensitive is `message`?',
                'criteria': ['Not urgent, exploratory', 'Wants an answer soon', 'Urgent, market is moving now']},
}


def chat_gate_start(message, lang='es'):
    """Lanza la decisión de Jev en paralelo (no frena el chat). None si no aplica."""
    if not available() or not (shadow_mode() or control('chat_gate')) or not message:
        return None
    state = {'message': str(message)[:2000], 'language': lang}
    return _POOL.submit(ask, state, CHAT_QUESTIONS, 'khipu_chat')


def _actual_route(out):
    steps = int((out or {}).get('steps') or 0)
    tools = [t.get('name') for t in (out or {}).get('tools_used') or [] if isinstance(t, dict)]
    src = (out or {}).get('answer_source')
    if src == 'local' or (steps == 0 and not tools):
        return 'local_fact'
    if steps <= 2 and len(tools) <= 2 and src != 'fallback':
        return 'needs_tools'
    return 'needs_deep_reasoning'


def chat_gate_finish(fut, out, message=None):
    """Compara la decisión de Jev con lo que hizo el chat y lo deja en sombra."""
    if fut is None:
        return None
    try:
        ans = fut.result(timeout=0.05) if fut.done() else None
        if ans is None:
            # todavía no llegó: se resuelve en segundo plano para no frenar la respuesta
            _POOL.submit(_finish_bg, fut, out, message)
            return None
        return _compare(ans, out, message)
    except Exception as e:  # noqa: BLE001
        log.info('decide: gate (%s)', type(e).__name__)
        return None


def _finish_bg(fut, out, message):
    try:
        ans = fut.result(timeout=TIMEOUT_S + 2)
        if ans:
            _compare(ans, out, message)
    except Exception:  # noqa: BLE001
        pass


def _num(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def decision_of(ans):
    """Respuesta cruda de Jev → decisión plana. La confianza de la ruta: `confidence` o, si no viene,
    la probabilidad de la opción elegida."""
    ans = ans if isinstance(ans, dict) else {}
    route = ans.get('route') or {}
    choice = route.get('choice')
    conf = _num(route.get('confidence'))
    if conf is None and isinstance(route.get('probabilities'), dict):
        conf = _num(route['probabilities'].get(choice))
    return {'route': choice if choice in CHAT_QUESTIONS['route']['criteria'] else None, 'confidence': conf,
            'mentions_company': _num((ans.get('mentions_company') or {}).get('noul')),
            'asks_trade': _num((ans.get('asks_trade') or {}).get('noul')),
            'about_portfolio': _num((ans.get('about_portfolio') or {}).get('noul')),
            'urgency': (ans.get('urgency') or {}).get('score')}


def chat_plan(fut, wait_s=None):
    """Jev AL MANDO del chat: → decisión {route, confidence, …} que el chat OBEDECE, o None (sin control,
    sin respuesta a tiempo o confianza < DECIDE_MIN_CONF) → el chat sigue como siempre. Nunca decide dinero:
    si la pregunta parece una orden, la ruta barata no se toma."""
    if fut is None or not control('chat_gate'):
        return None
    try:
        ans = fut.result(timeout=CONTROL_WAIT_S if wait_s is None else max(0.0, float(wait_s)))
    except Exception:  # noqa: BLE001 — no llegó a tiempo: manda el camino de siempre
        return None
    d = decision_of(ans)
    if not d['route'] or (d['confidence'] or 0) < MIN_CONF:
        return None
    if (d['asks_trade'] or 0) >= 0.5 and d['route'] in ('local_fact', 'offtopic'):
        return None
    return d


def _compare(ans, out, message):
    decision = decision_of(ans)
    actual = {'route': _actual_route(out), 'steps': (out or {}).get('steps'),
              'router': ((out or {}).get('router') or {}).get('by'),
              'tools': [t.get('name') for t in (out or {}).get('tools_used') or [] if isinstance(t, dict)],
              'source': (out or {}).get('answer_source'), 'elapsed_ms': (out or {}).get('elapsed_ms')}
    agree = (decision['route'] == actual['route']) if decision['route'] else None
    shadow('chat_gate', (message or '')[:200], decision, actual, agree)
    return decision
