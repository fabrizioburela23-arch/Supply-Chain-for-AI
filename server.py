"""
server.py — Khipu Finance v1
Backend proxy ligero para el ecosistema de inteligencia de inversión.

Corre con:   python server.py
Dependencias: pip install flask requests python-dotenv flask-caching anthropic

Modo de operación:
  - Sirve app.html en http://localhost:5050
  - Actúa como proxy de Finnhub / FMP / Marketstack / Claude (las API keys viven
    en variables de entorno — nunca en el navegador)
  - Cachea respuestas en memoria (flask-caching SimpleCache) para no gastar llamadas
  - El frontend detecta el puerto 5050 y enruta sus fetch a /api/* automáticamente
"""
import os
import re
import json
import time
import uuid
import logging
import hashlib
import hmac
import threading
import requests
from collections import defaultdict
from functools import wraps
from datetime import date, datetime, timedelta
from flask import Flask, Response, jsonify, send_file, request
from flask_caching import Cache

# PyJWT es opcional: si no está instalado, la API pública /v1/* queda deshabilitada
# pero el resto del servidor (proxy de datos, voz Khipu) sigue funcionando.
try:
    import jwt
    _HAS_JWT = True
except Exception:  # noqa: BLE001
    _HAS_JWT = False

# --- Config ---
from dotenv import load_dotenv
load_dotenv()  # Lee .env: FINNHUB_KEY, FMP_KEY, CLAUDE_KEY, MARKETSTACK_KEY, AI_MODEL_FAST/_DEEP…

app = Flask(__name__)
# Caché: interno (SimpleCache, por worker) por defecto; si existe REDIS_URL
# (plugin de Railway) se usa Redis automáticamente — compartido entre workers
# y sobrevive reinicios. Cero configuración manual: solo añadir la variable.
if os.getenv('REDIS_URL'):
    try:
        import redis as _redis_probe  # noqa: F401
        app.config['CACHE_TYPE'] = 'RedisCache'
        app.config['CACHE_REDIS_URL'] = os.getenv('REDIS_URL')
        app.config['CACHE_KEY_PREFIX'] = 'khipu:'
    except Exception:  # noqa: BLE001
        app.config['CACHE_TYPE'] = 'SimpleCache'
else:
    app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # 5 min por defecto
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024  # 1 MB — el contexto de Canvas
# (catálogo de ~555 empresas + quotes) supera 64 KB; sigue acotado y con rate-limit.
cache = Cache(app)


# ── Caché: NUNCA guardar errores (auditoría estructural #5) ─────────────────
# Flask-Caching guardaba CUALQUIER respuesta: un 502 de /vendor quedaba 7 días,
# un fallo de noticias 30 min, etc. `_cacheable_response` deja pasar solo
# status < 400. Se instala como response_filter por defecto de TODO
# @cache.cached (incluidos los que se añadan en el futuro) envolviendo el
# método del objeto `cache`; un response_filter explícito se combina con este.
def _response_status(rv):
    """Status de lo que devuelve una vista: Response, (body, status[, headers]),
    (body, headers), dict/str (→ 200) o HTTPException ya convertida."""
    try:
        if isinstance(rv, tuple):
            body = rv[0] if rv else None
            if len(rv) >= 2 and isinstance(rv[1], int):
                return rv[1]
            if len(rv) >= 2 and isinstance(rv[1], str) and rv[1][:3].isdigit():
                return int(rv[1][:3])
            return int(getattr(body, 'status_code', 200) or 200)
        return int(getattr(rv, 'status_code', 200) or 200)
    except Exception:  # noqa: BLE001
        return 500


_DEGRADED_HDR = 'X-Khipu-Degraded'


def _degraded(resp):
    """Marca una respuesta 200 hecha de RESPALDO (upstream caído → lista vacía,
    órbitas sintéticas, series a medias…) para que NO se cachee: si no, el
    fallo quedaba servido 30 min-24 h aunque el proveedor volviera."""
    resp.headers[_DEGRADED_HDR] = '1'
    resp.headers['Cache-Control'] = 'no-store'
    return resp


def _cacheable_response(rv):
    body = rv[0] if isinstance(rv, tuple) and rv else rv
    headers = getattr(body, 'headers', None)
    if headers is not None and headers.get(_DEGRADED_HDR):
        return False
    return _response_status(rv) < 400


_cache_cached_orig = cache.cached

# Caché NEGATIVA corta: un respaldo (_degraded) o un 502/503/504 de upstream
# NO se guarda en la caché normal (sería servirlo 30 min-7 días), pero sin
# nada, mientras el proveedor está caído CADA petición volvía a esperarlo
# (hasta 25 s en /vendor) y unos pocos visitantes agotaban los hilos de
# gunicorn. Se repite la misma respuesta de fallo _NEG_CACHE_S segundos (o
# menos: nunca más que la caché positiva de la ruta).
_NEG_CACHE_S = 60
_NEG_STATUSES = (502, 503, 504)


def _neg_cache_key(query_string=False):
    key = 'neg:' + request.path
    if query_string and request.args:
        key += '?' + '&'.join(f'{k}={v}' for k, v in sorted(request.args.items(multi=True)))
    return key[:400]


def _with_negative_cache(f, query_string=False, ttl=None):
    @wraps(f)
    def wrapper(*a, **k):
        key = None
        try:
            key = _neg_cache_key(query_string)
            hit = cache.get(key)
        except Exception:  # noqa: BLE001 — la caché nunca rompe la ruta
            hit = None
        if hit:
            body, status, mimetype = hit
            resp = app.response_class(body, status=status, mimetype=mimetype)
            resp.headers[_DEGRADED_HDR] = '1'
            resp.headers['Cache-Control'] = 'no-store'
            resp.headers['X-Khipu-Neg-Cache'] = '1'
            return resp
        rv = f(*a, **k)
        try:
            body0 = rv[0] if isinstance(rv, tuple) and rv else rv
            hdrs = getattr(body0, 'headers', None)
            degraded = hdrs is not None and hdrs.get(_DEGRADED_HDR)
            if key and (degraded or _response_status(rv) in _NEG_STATUSES):
                resp = app.make_response(rv)
                if not resp.is_streamed:
                    cache.set(key, (resp.get_data(), resp.status_code, resp.mimetype),
                              timeout=ttl or _NEG_CACHE_S)
                return resp
        except Exception:  # noqa: BLE001
            pass
        return rv
    return wrapper


def _cache_cached_ok_only(*args, **kwargs):
    user_filter = kwargs.get('response_filter')
    if user_filter is None:
        kwargs['response_filter'] = _cacheable_response
    else:
        kwargs['response_filter'] = lambda rv: _cacheable_response(rv) and user_filter(rv)
    deco = _cache_cached_orig(*args, **kwargs)
    qs = bool(kwargs.get('query_string'))
    # nunca más larga que la caché positiva de la ruta (/api/scalp/price: 2 s)
    try:
        pos_ttl = int(kwargs.get('timeout', args[0] if args else None) or app.config['CACHE_DEFAULT_TIMEOUT'])
    except (TypeError, ValueError):
        pos_ttl = _NEG_CACHE_S
    neg_ttl = max(1, min(_NEG_CACHE_S, pos_ttl))

    def apply(f):
        return deco(_with_negative_cache(f, query_string=qs, ttl=neg_ttl))
    return apply


cache.cached = _cache_cached_ok_only

# Fluidez: comprimir HTML/JS/JSON al vuelo (brotli/gzip) — el código de la app
# pesa ~1.9 MB sin comprimir; con esto baja ~75%. Defensivo: si el paquete no
# está instalado aún (deploy en curso), el server arranca igual sin comprimir.
try:
    from flask_compress import Compress
    app.config['COMPRESS_MIMETYPES'] = ['text/html', 'text/css', 'application/json',
                                        'application/javascript', 'text/javascript',
                                        'image/svg+xml']
    app.config['COMPRESS_MIN_SIZE'] = 1024
    Compress(app)
except Exception as _e:  # noqa: BLE001
    logging.getLogger('khipu').warning('flask-compress no disponible (%s) — sin compresión', _e)

logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(message)s')
log = logging.getLogger('khipu')
try:   # O2: LOG_JSON=on → una línea JSON por log (job_id/agente/proveedor/costo/latencia); sin la variable nada cambia
    from core.logjson import configure as _logjson_configure
    _logjson_configure()
except Exception as _e:  # noqa: BLE001
    log.warning('LOG_JSON no aplicado: %s', type(_e).__name__)

# ── Ontología (Fase 1, opcional) — /api/ontology/* ───────────────────────────
# Registro defensivo: si sqlalchemy no está instalado aún (deploy en curso) o
# DATABASE_URL no está configurada, el resto de la app sigue funcionando igual.
try:
    from ontology.api import ontology_bp
    app.register_blueprint(ontology_bp)
    # Crea las tablas que FALTEN (idempotente, NO destructivo). Antes solo se
    # creaban al correr la migración; las tablas `proposed_actions` y `alerts`
    # (Fases 3-4) se añadieron después → nunca se crearon en prod → sus endpoints
    # (agents/brief, proposals, alerts) daban HTTP 500. create_all con checkfirst
    # SOLO crea lo que no existe: events/objects/links quedan intactos con sus
    # datos. Bug detectado 2026-07-14 por la auditoría; el docstring de init_schema
    # ya decía que debía llamarse en boot, pero la llamada faltaba.
    try:
        from ontology.db import ontology_available, init_schema
        if ontology_available():
            init_schema()
    except Exception as _e2:  # noqa: BLE001
        log.warning('init_schema (ontología) no corrió (la app sigue): %s', _e2)
except Exception as _e:  # noqa: BLE001
    log.warning('Ontología no registrada (opcional): %s', _e)

# ── PHASE 2 · Agent Research Swarm (opcional) — /api/research/* ─────────────
# Claims con evidencia/contra-evidencia, horizonte y confianza calculada;
# tablas research_* creadas por init_schema. Sin DATABASE_URL responde 503.
try:
    from research.api import research_bp
    app.register_blueprint(research_bp)
except Exception as _e:  # noqa: BLE001
    log.warning('Investigación (Phase 2) no registrada (opcional): %s', _e)

# ── PHASE 3 + World Monitor + Corretaje multi-cliente + MCP (2026-09-30) ─────
# Cada módulo es OPCIONAL (patrón try/except): si falta o falla al importar, la
# app arranca igual. Registro centralizado aquí para que los módulos no toquen
# server.py. Blueprints: /api/world/* · /api/committee/* · /api/brokerage/* · /mcp
import importlib as _importlib
for _mod, _bp_name in (('core.world', 'world_bp'), ('research.committee_api', 'committee_bp'),
                       ('brokerage.api', 'brokerage_bp'), ('mcp_server.api', 'mcp_bp'),
                       ('core.space', 'space_bp'), ('core.portfolio_ai', 'portfolio_ai_bp'),
                       ('core.khipu_chat', 'khipu_chat_bp'),
                       ('core.portfolio_reports_api', 'portfolio_reports_bp'), ('core.decide_api', 'decide_bp'),
                       ('core.ledger_api', 'ledger_bp'),    # INFRA_OPERATIVA paso 6: libro de decisiones /api/ledger/*
                       ('core.governance_api', 'governance_bp'),    # paso 9: registro de gobernanza /api/governance/*
                       ('core.prices_api', 'prices_bp')):   # BRECHAS bloque 2: historia de precios /api/prices/*
    try:
        app.register_blueprint(getattr(_importlib.import_module(_mod), _bp_name))
    except Exception as _e:  # noqa: BLE001
        log.warning('Módulo %s no registrado (opcional): %s', _mod, _e)

# ── Motor de matrices (Etapa 3, opcional) — /api/matrix/* ────────────────────
try:
    from matrix.api import matrix_bp
    app.register_blueprint(matrix_bp)
except Exception as _e:  # noqa: BLE001
    log.warning('Motor de matrices no registrado (opcional): %s', _e)

# ── Vistas de camino crítico (INFRA_OPERATIVA paso 4) — /api/hot/* ───────────
# GraphCore + Impact construidos UNA vez por versión del grafo (Postgres o, sin base, el snapshot) por un
# solo hilo; /api/matrix/{status,impact,metrics,factors,factor/fire} delegan en ellas. Nunca /v1/*.
try:
    from core.hotviews.api import hot_bp
    app.register_blueprint(hot_bp)
except Exception as _e:  # noqa: BLE001
    log.warning('Vistas rápidas no registradas (opcional): %s', _e)

# ── Ontología nivel 2 (tensores; sin BD) — /api/tensor/* ─────────────────────
try:
    from matrix.tensor_api import tensor_bp
    app.register_blueprint(tensor_bp)
except Exception as _e:  # noqa: BLE001
    log.warning('Motor de tensores no registrado (opcional): %s', _e)

# ── Sala de Situación geopolítica (opcional) — /api/geo/* ────────────────────
try:
    from core.geosit import geo_bp
    app.register_blueprint(geo_bp)
except Exception as _e:  # noqa: BLE001
    log.warning('Sala de Situación no registrada (opcional): %s', _e)

# ── O1 (misión de reparación): chequeo del sistema — /api/ops/* ─────────────
try:
    from core.ops_check import ops_bp
    app.register_blueprint(ops_bp)
except Exception as _e:  # noqa: BLE001
    log.warning('Chequeo del sistema no registrado (opcional): %s', _e)

# ── Khipus OS: perfiles de los agentes (funciona sin BD) — /api/agents/* ─────
try:
    from core.agents_api import agents_bp
    app.register_blueprint(agents_bp)
except Exception as _e:  # noqa: BLE001
    log.warning('Perfiles de agentes no registrados (opcional): %s', _e)


# ── Screener de crecimiento explosivo — /api/screener/growth ─────────────────
@app.route('/api/screener/growth')
def screener_growth():
    """Ranking de señales de crecimiento explosivo sobre TODO el universo
    cotizable del grafo (~410 símbolos, multi-bolsa). Momentum 5/20/60d +
    centralidad PageRank + MA20. El calentador de fondo llena la cobertura en
    ~7 min tras el arranque; la respuesta declara cuánta hay. Señales, no
    asesoría."""
    try:
        from core.screener import screen_growth
        top = int(request.args.get('top', 30))
        return jsonify(screen_growth(top=top))
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:160]}), 500


# Rutas de administración de la voz (PIN de operador) → core/voice_api.py; `_require_operator` lo usan
# también otras rutas de aquí (p. ej. /api/diag/recent).
from core.pin import require_operator as _require_operator  # noqa: E402

# ── Re-migración de la ontología por variable de entorno (para Fabrizio) ──────
# Poner REMIGRATE_ON_BOOT=<NOMBRE DE LA BASE> en Railway (el de
# `SELECT current_database()`, p. ej. 'railway') → al reiniciar, re-crea el
# GRAFO desde el repo: 949 empresas + links + hechos temporales + los ~69
# factores sistémicos (latentes) y 28 asientos de la capa multicapa.
# DESTRUCTIVO (borra objetos/eventos/links). Auditoría #6: el valor ya NO es
# '1'/'true' — scripts/migrate_v0_to_ontology.check_reset_allowed exige que sea
# EXACTAMENTE el nombre de la base, se niega si broker_* (libro de clientes)
# tiene filas y solo borra links/events/objects (MCP, research, alertas y
# propuestas se conservan); aquí solo se mira que la variable exista.
# Se corre UNA vez y luego se QUITA la variable. Nunca bloquea el arranque.
if os.getenv('REMIGRATE_ON_BOOT', '').strip():
    try:
        from scripts.migrate_v0_to_ontology import run_migration
        log.warning('REMIGRATE_ON_BOOT activo — re-migrando la ontología completa desde el repo…')
        run_migration(reset=True, log=lambda m: log.warning('  [remigrate] %s', m))
        log.warning('REMIGRATE_ON_BOOT: listo. QUITA la variable REMIGRATE_ON_BOOT de Railway ahora.')
    except Exception as _e:  # noqa: BLE001
        log.error('REMIGRATE_ON_BOOT falló (la app sigue): %s', _e)

# ── R5 (misión de reparación): reloj del servidor para lo "diario" ───────────
# Antes lo periódico colgaba del refresco de capitalizaciones (solo con tráfico).
# KHIPU_SCHEDULER=off lo apaga (tests). Las tareas se registran aquí; nunca IA.
try:
    from core import scheduler as _sched
    try:
        from research.runner import recover_orphans_job as _recover_orphans_job
        from research.runner import resume_deferred_job as _resume_deferred
        _sched.register('research_recover_orphans', _recover_orphans_job, every_s=120, run_at_start=False)   # R11: por latido, cada 2 min
        _sched.register('research_resume_deferred', _resume_deferred, every_s=600)
    except Exception as _e:  # noqa: BLE001
        log.warning('scheduler: research no registrado (%s)', type(_e).__name__)
    try:   # C10: calificar predicciones vencidas 1×/día SIN depender de que alguien abra el mapa
        from core.live_caps import _daily_outcomes as _outcomes_daily
        _sched.register('research_outcomes_daily', _outcomes_daily, every_s=3600)
    except Exception as _e:  # noqa: BLE001
        log.warning('scheduler: outcomes no registrado (%s)', type(_e).__name__)
    try:   # W1: el World Monitor se precalienta solo (el 1.er visitante ya no ve "cargando")
        from core import world as _world
        _sched.register('world_prewarm', _world.prewarm, every_s=600, run_at_start=True)
    except Exception as _e:  # noqa: BLE001
        log.warning('scheduler: world_prewarm no registrado (%s)', type(_e).__name__)
    try:   # 2026-10-05: fundamentales EN VIVO de todas las cotizadas, por tandas (margen, crecimiento, ingresos…)
        from core import live_fundamentals as _lf
        _sched.register('live_fundamentals', _lf.refresh, every_s=300, run_at_start=True)
    except Exception as _e:  # noqa: BLE001
        log.warning('scheduler: live_fundamentals no registrado (%s)', type(_e).__name__)
    try:   # INFRA_OPERATIVA paso 4: precalentar las vistas rápidas al arrancar (incluida la importación de
        # scipy) y, cada 30 s, comparar kh_versions con lo conocido por si se perdió un aviso (LISTEN/NOTIFY)
        from core.hotviews import builder as _hv_builder, signals as _hv_signals

        def _hot_views_tick():
            _hv_builder.start(eager=True)
            try:
                return _hv_signals.poll()
            except Exception as _pe:  # noqa: BLE001
                return {'poll_error': type(_pe).__name__}
        _sched.register('hot_views', _hot_views_tick, every_s=30, run_at_start=True)
    except Exception as _e:  # noqa: BLE001
        log.warning('scheduler: hot_views no registrado (%s)', type(_e).__name__)
    try:   # INFRA_OPERATIVA paso 6: sellador del libro (cadena de hashes sobre events, decisiones y broker_audit)
        from ontology.db import ontology_available as _ledger_db_on
        if _ledger_db_on():
            from core import ledger as _ledger
            _sched.register('ledger_seal', _ledger.seal_job, every_s=_ledger.SEAL_EVERY_S, run_at_start=True)
            # paso 7: ancla diaria (una fila por día; GET /api/ledger/anchor la publica y GitHub Actions la guarda)
            # + detección de restauración (linaje). Cada hora: si el ancla del día ya existe, no hace nada.
            _sched.register('ledger_anchor', _ledger.anchor_job, every_s=3600, run_at_start=True)
            # paso 26 (D3): purga por retención (cuerpos de chat/qué-pasaría-si > 90 días → NULL, el sha queda) +
            # claves viejas de la sombra a HMAC; UNA vez por día UTC (la tarea mira cada hora). Y los puntos de
            # control del grafo: apagados hasta que la ontología pase ledger.retention.checkpoint_min_events.
            from core import retention as _retention
            from ontology import checkpoints as _checkpoints
            _sched.register('retention_daily', _retention.daily_job, every_s=3600, run_at_start=False)
            _sched.register('graph_checkpoints', _checkpoints.job, every_s=3600, run_at_start=False)
            # paso 24 (§5.6): muestra nocturna de replays — 50 decisiones deterministas al azar de las últimas 24 h +
            # TODAS las de dinero, UNA vez por día UTC (la tarea mira cada hora); un 'differs' pone el 🩺 en rojo
            from core import replay as _replay_mod
            _sched.register('ledger_replay_sample', _replay_mod.sample_job, every_s=3600, run_at_start=False)
    except Exception as _e:  # noqa: BLE001
        log.warning('scheduler: ledger_seal no registrado (%s)', type(_e).__name__)
    try:   # INFRA_OPERATIVA paso 9: release de gobernanza vigente (la base manda; barato: 2 consultas indexadas)
        from core import governance as _gov_mod
        _sched.register('governance_refresh', _gov_mod.refresh_job, every_s=60, run_at_start=False)
    except Exception as _e:  # noqa: BLE001
        log.warning('scheduler: governance_refresh no registrado (%s)', type(_e).__name__)
    try:   # INFRA_OPERATIVA paso 16: avances de ejecución de las órdenes abiertas → broker_fills + decision_outcomes
        from ontology.db import ontology_available as _fills_db_on
        if _fills_db_on():
            from brokerage.service import poll_fills_job as _poll_fills
            _sched.register('broker_fills', _poll_fills, every_s=60, run_at_start=False)
    except Exception as _e:  # noqa: BLE001
        log.warning('scheduler: broker_fills no registrado (%s)', type(_e).__name__)
    try:   # BRECHAS bloque 2: cierres del día + FX + fotos diarias (días hábiles tras las 22:00 UTC, en su hilo;
        # sin base no hace nada). El relleno de 5 años NO está aquí: solo a pedido del operador con PIN.
        from core import prices_store as _prices_store
        _sched.register('prices_eod_daily', _prices_store.daily_tick, every_s=900, run_at_start=False)
    except Exception as _e:  # noqa: BLE001
        log.warning('scheduler: prices_eod_daily no registrado (%s)', type(_e).__name__)
    try:   # O1: humo 5 min tras cada arranque (= tras cada deploy) y luego 1×/día, guardado en ops_checks
        from core.ops_check import scheduled as _ops_scheduled, FIRST_AFTER_BOOT_S as _OPS_FIRST
        _sched.register('ops_daily_check', _ops_scheduled, every_s=_OPS_FIRST, run_at_start=False)
    except Exception as _e:  # noqa: BLE001
        log.warning('scheduler: ops_daily_check no registrado (%s)', type(_e).__name__)
    if _sched.enabled():
        _sched.start()
except Exception as _e:  # noqa: BLE001
    log.warning('scheduler no arrancó: %s', _e)

# Config compartida server/ontology (keys de IA, Finnhub, timeout) → core/config.py
# Helpers compartidos: cascada de IA, quote crudo y GET saneado → core/*.py
from core.config import (AI_ORDER, CLAUDE, FINNHUB, GEMINI_KEY,
                         GEMINI_MODEL, HTTP_TIMEOUT, NVIDIA_KEY, NVIDIA_MODEL)
from core.http import _rate_buckets, _rate_limit, _safe_get, _safe_ticker, rate_limit, redact_secrets
# PIN de operador ÚNICO (auditoría #7): mismo contador por IP/global para
# /api/trade/*, /api/brokerage/* y /api/mcp/* — ver core/pin.py.
from core.pin import (client_ip as _client_ip, insecure_production_secret as _insecure_prod_secret,
                      require_pin as _require_pin, secret_key_default as _secret_key_default)
from core.ai import (_ai_complete, _ai_configured,
                     _complete_gemini, _complete_nvidia, _extract_json)
from core.quotes import _fetch_quote_raw


def _ai_route_now():
    """Ruta REAL de la IA por nivel (rápido/profundo) para el 🩺; nunca rompe el diagnóstico."""
    try:
        from core import ai as _ai_mod
        return _ai_mod.ai_route_state()
    except Exception:  # noqa: BLE001
        return None


def _ai_models_now():
    return (_ai_route_now() or {}).get('models')

FMP      = os.getenv('FMP_KEY', '')
MSTACK   = os.getenv('MARKETSTACK_KEY', '')

def _clean_env(v):
    """Limpia un valor de variable de entorno: quita espacios/saltos de línea y
    comillas que se cuelan al pegar en el panel de Railway (causa típica de un
    'Unauthorized' aunque la clave sea 'correcta')."""
    v = (v or '').strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        v = v[1:-1].strip()
    return v

# Grafo de Conocimiento Temporal: la memoria temporal vive en Postgres (ontología bitemporal, G(t, κ)) y en el
# cliente (modo nativo). Neo4j se RETIRÓ el 2026-10-13 (decisión #6 de Fabrizio): nadie lo leía. No reintroducirlo.

# Servicios adicionales (Khipu Finance v1)
# MiroFish (microservicio externo multi-agente) se retiró: su caso de uso lo
# cubren los motores INTERNOS — matrix/engine.py (cascada determinista) y
# core/sim_agents.py (debate de agentes). Ver docs/ESTADO.md.
ELEVENLABS_KEY      = os.getenv('ELEVENLABS_KEY', '')
ELEVENLABS_AGENT_ID = os.getenv('ELEVENLABS_AGENT_ID', '')
AV_KEY              = os.getenv('AV_KEY') or os.getenv('ALPHA_VANTAGE_KEY', '')
SECRET_KEY          = os.getenv('SECRET_KEY', 'khipu-dev-secret-change-me')
ALPACA_KEY          = _clean_env(os.getenv('ALPACA_KEY', ''))
ALPACA_SECRET       = _clean_env(os.getenv('ALPACA_SECRET', ''))
# Base de Alpaca. Normalizada a prueba de errores de pegado en Railway:
#  · quita comillas/espacios (_clean_env) y la barra final → evita '//v2/account';
#  · añade https:// si falta el esquema;
#  · quita el sufijo '/v2' o '/v1' si lo pegaron (→ '/v2/v2/account' = HTTP 404,
#    causa real de "Alpaca HTTP 404 / could not fetch equity").
def _norm_alpaca_base(v):
    v = (_clean_env(v) or 'https://paper-api.alpaca.markets').strip().rstrip('/')
    if not v.startswith('http'):
        v = 'https://' + v
    for _suf in ('/v2', '/v1'):
        if v.endswith(_suf):
            v = v[:-len(_suf)]
    return v.rstrip('/') or 'https://paper-api.alpaca.markets'
ALPACA_BASE         = _norm_alpaca_base(os.getenv('ALPACA_BASE', 'https://paper-api.alpaca.markets'))
# PIN que protege TODAS las rutas /api/trade/* (operan dinero real vía Alpaca).
# Sin TRADE_PIN configurado, el trading queda DESHABILITADO (seguro por defecto).
TRADE_PIN           = os.getenv('TRADE_PIN', '')
# Secreto de administrador para emitir claves /v1 de tiers de pago.
KHIPU_ADMIN_SECRET  = os.getenv('KHIPU_ADMIN_SECRET', '')

if _secret_key_default():
    if _insecure_prod_secret():
        # Auditoría #15: en producción es un riesgo real (tokens /ws, claves /v1,
        # derivación del cifrado del corretaje). No se cambia el comportamiento de
        # /v1 (API monetizada); se avisa FUERTE aquí, en /api/health y en 🩺.
        log.error('🚨 SECRET_KEY es la de por defecto EN PRODUCCIÓN — configura SECRET_KEY en Railway YA '
                  '(las firmas con ella son falsificables; OAuth de MCP queda desactivado)')
    else:
        log.warning('⚠️  SECRET_KEY is default — set SECRET_KEY env var in Railway before going live')

# ── Security config (Fase 2 — endurecimiento a producto) ────────────────────
# La CSP solo se aplica cuando el server sirve la app (modo servidor). En
# standalone puro (file://) no hay server, así que estas cabeceras no afectan
# ese modo. Todas son ajustables por env para poder desactivar al instante.
CSP_ENABLED            = os.getenv('CSP_ENABLED', 'true').lower() == 'true'
CSP_REPORT_ONLY        = os.getenv('CSP_REPORT_ONLY', 'false').lower() == 'true'

# Content-Security-Policy: restringe el origen de los scripts a los CDNs reales
# que usa la app (d3 y three.js desde cdnjs, chart.js desde jsdelivr) y bloquea
# framing, plugins y manipulación de <base>. 'unsafe-inline' sigue: los 4 bloques
# inline que quedan en app.html, el marcador del shell viejo que inyecta sw.js y
# miles de onclick/estilos inline (G5-06, 2026-10-13: el resto del JS de app.html
# vive en engine/app_*.js, mismo origen = 'self'; nonces/hashes después). upgrade-insecure-requests se añade
# aparte, solo bajo HTTPS (no rompe dev local).
# G5-09 (lote I1): SIN 'unsafe-eval' (grep eval/new Function/setTimeout(texto) en
# app.html, engine/, nodes/, sim/ y en d3/three/chart/satellite → 0 usados; el
# new Function de d3-dsv solo corre con d3.csv*, que la app no usa) y connect-src
# SOLO a los hosts que el navegador llama de verdad: el propio servidor; el
# WebSocket de Finnhub (app.html LivePrices); la voz de ElevenLabs (URL firmada
# wss://api[.región].elevenlabs.io que entrega /api/voice/session); y los CDNs que
# el service worker (sw.js CDN_HOSTS) vuelve a pedir con fetch() — su CSP es la
# de /sw.js, esta misma. data:/blob: para descargas generadas en el navegador.
# Emergencia: CSP_REPORT_ONLY=true (avisa sin bloquear) o CSP_ENABLED=false.
CSP_CONNECT_SRC = ("'self' data: blob: wss://ws.finnhub.io wss://*.elevenlabs.io https://*.elevenlabs.io "
                   "https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com "
                   "https://fonts.googleapis.com https://fonts.gstatic.com")
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' "
        "https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' data: https://fonts.gstatic.com; "
    "img-src 'self' data: blob: https:; "
    f"connect-src {CSP_CONNECT_SRC}; "
    "worker-src 'self' blob:; "
    "frame-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "object-src 'none'"
)

# ── Límite de tasa: la implementación vive en core/http.py (importada arriba)
# para que matrix/ y ontology/ puedan usarla sin importar el server — que es
# justo la circularidad que core/ existe para romper. Las 46 rutas de este
# archivo siguen usando @rate_limit igual que antes. ───────────────────────


@app.after_request
def _add_security_headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['X-XSS-Protection'] = '1; mode=block'
    resp.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    resp.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=(self)'
    resp.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
    is_https = request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https'
    if CSP_ENABLED:
        csp = CONTENT_SECURITY_POLICY
        # upgrade-insecure-requests solo bajo HTTPS — en http://localhost rompería /api/*
        if is_https:
            csp += '; upgrade-insecure-requests'
        header = 'Content-Security-Policy-Report-Only' if CSP_REPORT_ONLY else 'Content-Security-Policy'
        resp.headers[header] = csp
    # HSTS only on HTTPS (Railway)
    if is_https:
        resp.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return resp


# ── CORS: la API pública /v1/* es para terceros (auth por API key) → se permite
# cualquier origen. El resto (/api/* interno) queda same-origin: sin cabeceras
# CORS el navegador bloquea las llamadas cross-origin, que es lo seguro. ─────
@app.after_request
def _add_cors_for_public_api(resp):
    if request.path.startswith('/v1/'):
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-KHIPU-Key'
        resp.headers['Access-Control-Max-Age'] = '86400'
    return resp


@app.after_request
def _add_graph_version_header(resp):
    """§4.1: toda respuesta /api lleva la versión del grafo que el proceso conoce (en memoria, sin ir a la
    base) para que el cliente invalide su caché. Las rutas de vistas ya ponen la de SU generación."""
    try:
        if request.path.startswith('/api/') and 'X-Khipu-Graph-Version' not in resp.headers:
            from core.hotviews.signals import known as _hv_known
            _v = _hv_known().get('v')
            if _v:
                resp.headers['X-Khipu-Graph-Version'] = str(_v)
    except Exception:  # noqa: BLE001
        pass
    return resp


@app.after_request
def _log_request(resp):
    log.info('%s %s -> %s', request.method, request.path, resp.status_code)
    return resp


# ── Red de seguridad: ningún secreto sale en una respuesta JSON (auditoría #13)
# Hay ~100 `str(e)` devueltos al cliente; si una excepción trae la URL con
# &token= o una key, aquí se tapa. Valores exactos de las env secretas (≥ 16
# caracteres —las API keys reales lo son— para no tocar cifras legítimas: un
# TRADE_PIN numérico corto NUNCA se busca aquí) en todo JSON < 256 KB; además,
# en errores (status ≥ 400), los patrones key=/token=/Bearer. Corre ANTES de
# comprimir (flask-compress se registró primero → su after_request va al final).
_REDACT_MAX_BYTES = 256 * 1024
_REDACT_EXEMPT_PATHS = frozenset({'/api/ws-key'})   # entrega A PROPÓSITO la key de WebSocket
# /v1/* (API monetizada) queda fuera: su comportamiento NO se toca (CLAUDE.md).


_REDACT_TEXT_ERR_TYPES = ('text/plain', 'text/html')   # páginas de error (status ≥ 400) también


@app.after_request
def _redact_secrets_in_json(resp):
    try:
        is_json = resp.mimetype == 'application/json'
        is_text_err = resp.mimetype in _REDACT_TEXT_ERR_TYPES and resp.status_code >= 400
        if ((not is_json and not is_text_err) or resp.direct_passthrough or resp.is_streamed
                or request.path in _REDACT_EXEMPT_PATHS or request.path.startswith('/v1/')
                or (resp.content_length or 0) > _REDACT_MAX_BYTES):
            return resp
        data = resp.get_data(as_text=True)
        if len(data) > _REDACT_MAX_BYTES:
            return resp
        red = data
        for v in _secret_values_for_scan():
            if v in red:
                red = red.replace(v, '••••')
        if resp.status_code >= 400:
            red = redact_secrets(red, min_len=_REDACT_MIN_LEN)
        if red != data:
            resp.set_data(red)
            log.warning('secreto tapado en la respuesta de %s (revisar el manejo de errores)', request.path)
    except Exception:  # noqa: BLE001 — nunca romper una respuesta por esto
        pass
    return resp


_REDACT_MIN_LEN = 16


def _secret_values_for_scan():
    from core.http import secret_values
    return secret_values(min_len=_REDACT_MIN_LEN, extra=(CLAUDE, GEMINI_KEY, NVIDIA_KEY, FINNHUB, FMP, MSTACK, AV_KEY,
                                           ELEVENLABS_KEY, ALPACA_KEY, ALPACA_SECRET, KHIPU_ADMIN_SECRET,
                                           SECRET_KEY))


# ----------------------------------------------------------------------------
# Servir la app
# ----------------------------------------------------------------------------
# Fix definitivo del "no veo los cambios": app.html se sirve SIEMPRE fresco
# (no-cache) y el server le inyecta ?v=<versión del SW> a cada <script src>.
# Al bumpear sw.js (regla de despliegue #1) cambian TODAS las URLs de JS →
# el navegador baja el código nuevo aunque tuviera el viejo cacheado 1h.
_APP_HTML_CACHE = {'ver': None, 'html': None, 'mtime': None}


def _sw_version():
    """Lee la versión del caché del Service Worker (khipu-finance-vN) de sw.js."""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sw.js'), 'r', encoding='utf-8') as f:
            m = re.search(r'khipu-finance-v(\d+)', f.read(2048))
        return m.group(1) if m else '0'
    except Exception:  # noqa: BLE001
        return '0'


def _versioned_app_html():
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, 'app.html')
    ver = _sw_version()
    try:
        mtime = os.path.getmtime(path)
    except Exception:  # noqa: BLE001
        mtime = None
    if _APP_HTML_CACHE['html'] is None or _APP_HTML_CACHE['ver'] != ver or _APP_HTML_CACHE['mtime'] != mtime:
        with open(path, 'r', encoding='utf-8') as f:
            html = f.read()
        html = re.sub(r'src="((?:engine|nodes|sim|vendor)/[^"?]+\.js)"',
                      lambda m: 'src="' + m.group(1) + '?v=' + ver + '"', html)
        _APP_HTML_CACHE.update(ver=ver, html=html, mtime=mtime)
    return _APP_HTML_CACHE['html']


@app.route('/')
def index():
    resp = app.response_class(_versioned_app_html(), mimetype='text/html')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    return resp


# --- PWA: Service Worker + manifest (solo útiles en modo servidor / http) ---
@app.route('/sw.js')
def service_worker():
    resp = send_file('sw.js', mimetype='application/javascript')
    resp.headers['Service-Worker-Allowed'] = '/'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


_MANIFEST = (
    '{'
    '"name":"Khipus Finance Intelligence","short_name":"Khipu","display":"standalone",'
    '"start_url":"/","scope":"/","background_color":"#F4F1EA","theme_color":"#1A1813",'
    '"description":"Inteligencia financiera sobre la cadena de valor global de IA, semiconductores y espacio",'
    '"icons":[{"src":"/icon.svg","sizes":"any","type":"image/svg+xml","purpose":"any"}]'
    '}'
)


@app.route('/manifest.webmanifest')
def manifest():
    return app.response_class(_MANIFEST, mimetype='application/manifest+json')


_ICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
    '<rect width="512" height="512" rx="96" fill="#1A1813"/>'
    '<circle cx="160" cy="200" r="40" fill="#7B2FBE"/>'
    '<circle cx="352" cy="170" r="46" fill="#1B6DB5"/>'
    '<circle cx="270" cy="340" r="54" fill="#0F8C5F"/>'
    '<line x1="160" y1="200" x2="352" y2="170" stroke="#D9A520" stroke-width="10"/>'
    '<line x1="352" y1="170" x2="270" y2="340" stroke="#D9A520" stroke-width="10"/>'
    '<line x1="160" y1="200" x2="270" y2="340" stroke="#D9A520" stroke-width="10"/>'
    '</svg>'
)


@app.route('/icon.svg')
def icon():
    return app.response_class(_ICON, mimetype='image/svg+xml')


# Serve JS modules — nodes/, engine/, sim/ are not in Flask's static folder
_APP_DIR = os.path.dirname(os.path.abspath(__file__))

def _js_cache_headers(resp):
    """URLs versionadas (?v=N, las inyecta index()) → inmutables 1 año: las
    recargas no vuelven a bajar NADA de código. Sin versión → 1h como antes.
    flask-compress salta respuestas en streaming (is_streamed) y
    send_from_directory SIEMPRE streamea — bufferizamos el archivo en memoria
    (get_data) para que comprima; son archivos de decenas/cientos de KB."""
    resp.direct_passthrough = False
    resp.get_data()   # materializa la respuesta → is_streamed=False → comprime
    if request.args.get('v'):
        resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    else:
        resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp


@app.route('/nodes/<path:filename>')
def serve_nodes(filename):
    from flask import send_from_directory
    resp = send_from_directory(os.path.join(_APP_DIR, 'nodes'), filename, mimetype='application/javascript')
    return _js_cache_headers(resp)

@app.route('/engine/<path:filename>')
def serve_engine(filename):
    from flask import send_from_directory
    resp = send_from_directory(os.path.join(_APP_DIR, 'engine'), filename, mimetype='application/javascript')
    return _js_cache_headers(resp)

@app.route('/sim/<path:filename>')
def serve_sim(filename):
    from flask import send_from_directory
    resp = send_from_directory(os.path.join(_APP_DIR, 'sim'), filename, mimetype='application/javascript')
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp


# ── /vendor — proxy de librerías y texturas externas (mismo origen) ──────────
# Sirve d3/three/chart/satellite y las texturas de la Tierra desde el propio
# servidor, para que la app funcione en redes que bloquean cdnjs/jsdelivr/unpkg.
_VENDOR_MAP = {
    'd3.min.js':            'https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js',
    'three.min.js':         'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js',
    'chart.umd.min.js':     'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js',
    'satellite.min.js':     'https://cdn.jsdelivr.net/npm/satellite.js@4.1.4/dist/satellite.min.js',
    'earth-blue-marble.jpg':'https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg',
    'earth-topology.png':   'https://unpkg.com/three-globe/example/img/earth-topology.png',
    'earth-dark.jpg':       'https://unpkg.com/three-globe/example/img/earth-dark.jpg',
    # Mapa mundial vectorial (TopoJSON, Natural Earth 110m — dominio público)
    # para el World Monitor y el Space Monitor (engine/worldmonitor.js, engine/spacemonitor.js)
    'world-110m.json':      'https://unpkg.com/world-atlas@2.0.2/countries-110m.json',
}


@app.route('/vendor/<path:name>')
@rate_limit(limit=120, window=60)
@cache.cached(timeout=604800)  # 7 días (solo 200; un fallo se repite 60 s: caché negativa)
def vendor(name):
    url = _VENDOR_MAP.get(name)
    if not url:
        return jsonify({'error': 'recurso desconocido', 'error_en': 'unknown vendor asset'}), 404
    try:
        # 10 s (antes 25): con el CDN colgado cada carga retenía un hilo 25 s.
        r = requests.get(url, timeout=10, headers={'User-Agent': 'KhipuFinance/1.0'})
        if not r.ok:
            return jsonify({'error': f'el CDN respondió HTTP {r.status_code}',
                            'error_en': f'CDN returned HTTP {r.status_code}'}), 502
        ctype = (r.headers.get('Content-Type') or '').split(';')[0] or \
            ('application/javascript' if name.endswith('.js') else 'application/octet-stream')
        resp = app.response_class(r.content, mimetype=ctype)
        resp.headers['Cache-Control'] = 'public, max-age=604800'
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'CDN no disponible', 'error_en': 'CDN unavailable',
                        'detail': _diag_redact(e)[:120]}), 502


# ----------------------------------------------------------------------------
# Health check / data-health (keys presentes + estado de subsistemas)
# ----------------------------------------------------------------------------
@app.route('/api/vocabulary')
def api_vocabulary():
    """REGISTRO ÚNICO del vocabulario (tipos de objeto, tipos de relación con su
    criticidad, tipos de fuente). El cliente debe consumir ESTO en vez de
    mantener sus propias copias — antes el vocabulario estaba duplicado en 5
    sitios y ya había divergido. Añadir un sector/tipo = editar
    ontology/vocabulary.json, no código. No necesita base de datos."""
    try:
        from ontology.vocabulary import snapshot
        snap = snapshot()
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': f'vocabulario no disponible: {str(e)[:120]}'}), 500
    # Categorías del catálogo (data/categories.json = fuente única, lote 2026-10-14): las 108 de hoy + las nuevas
    # aprobadas por defecto (con 0 empresas hasta que el importador las use), alias → id consolidado y cuántas
    # empresas tiene cada una en la generación vigente. Sin el JSON, el vocabulario sale igual que antes.
    cats_sha = ''
    try:
        from ontology.vocabulary import categories as _cats, category_aliases as _cat_alias, categories_doc as _cdoc
        cats = _cats()
        if cats:
            alias = _cat_alias()
            counts = {k: 0 for k in cats}
            try:
                from core.hotviews import hot as _hot
                for n in (_hot.graph().snapshot or {}).get('nodes') or []:
                    cid = alias.get(str(n.get('cat') or ''))
                    if cid in counts:
                        counts[cid] += 1
            except Exception:  # noqa: BLE001
                pass
            for k, v in cats.items():
                v['companies'] = counts[k]
            snap['categories'] = cats
            snap['category_aliases'] = {a: c for a, c in alias.items() if a != c}
            snap['sectors'] = _cdoc().get('sectors') or {}
            snap['categories_as_of'] = _cdoc().get('as_of')
            cats_sha = hashlib.sha256(json.dumps(cats, sort_keys=True).encode('utf-8')).hexdigest()[:8]
    except Exception as e:  # noqa: BLE001
        snap['categories_error'] = str(e)[:120]
    resp = jsonify(snap)
    # Cambia poco → cacheable, pero versionado para invalidar al editarlo. GV-07 (paso 9): el ETag es el HASH del
    # artefacto `ontology.schema` del release vigente (antes "vocab-1" fijo: un vocabulario editado sin subir la
    # versión no invalidaba ningún caché).
    resp.headers['Cache-Control'] = 'public, max-age=300'
    try:
        from core import governance as _g
        resp.headers['ETag'] = f'"vocab-{_g.artifact_hash_of("ontology.schema")[:16]}{"-" + cats_sha if cats_sha else ""}"'
        resp.headers['X-Khipu-Release'] = _g.release()[0][:16]
    except Exception:  # noqa: BLE001
        resp.headers['ETag'] = f'"vocab-{snap.get("version", 0)}{"-" + cats_sha if cats_sha else ""}"'
    return resp


@app.route('/api/vocabulary/unknown')
def api_vocabulary_unknown():
    """Diagnóstico: valores vistos que NO están en el registro. La regla del
    proyecto es que nada se clasifique en silencio; si algo aparece aquí, o es
    basura de ingesta o falta añadirlo a vocabulary.json."""
    try:
        from ontology.vocabulary import unknown_report
        rep = unknown_report()
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:120]}), 500
    return jsonify({'unknown': rep,
                    'clean': not rep,
                    'hint': 'Si un valor es legítimo, añádelo a ontology/vocabulary.json'})


# Errores de Flask en /api/*, /mcp y /oauth → JSON (antes: página HTML por
# defecto, y el navegador mostraba "Unexpected token '<'" — incidente 2026-09-29).
_JSON_ERR_PREFIXES = ('/api/', '/mcp', '/oauth', '/v1/', '/.well-known/')


def _json_error(code, es, en):
    from werkzeug.exceptions import HTTPException  # noqa: F401 (import local, barato)

    def handler(e):
        if request.path.startswith(_JSON_ERR_PREFIXES):
            if code >= 500:
                log.warning('HTTP %s en %s: %s', code, request.path, str(e)[:200])
            resp = jsonify({'error': es, 'error_en': en, 'status': code})
            if getattr(e, 'valid_methods', None):
                resp.headers['Allow'] = ', '.join(e.valid_methods)
            return resp, code
        return e if hasattr(e, 'get_response') else (str(e), code)
    return handler


for _code, _es, _en in ((400, 'solicitud inválida', 'bad request'), (404, 'no encontrado', 'not found'),
                        (405, 'método no permitido', 'method not allowed'),
                        (413, 'el contenido es demasiado grande (máx. 1 MB)', 'payload too large (max 1 MB)'),
                        (500, 'error interno del servidor', 'internal server error')):
    app.register_error_handler(_code, _json_error(_code, _es, _en))


@app.route('/api/health')
def health():
    # Sin llamadas de red: /api/health debe ser instantáneo. (Antes pagaba
    # hasta 2s de timeout sondeando MiroFish, ya retirado.)
    return jsonify({
        'server': True,
        'app': 'Khipus Finance Intelligence',
        'assistant': 'Khipu',
        'finnhub': bool(FINNHUB),
        'fmp': bool(FMP),
        'claude': bool(CLAUDE),
        'gemini': bool(GEMINI_KEY),
        'nvidia': bool(NVIDIA_KEY),
        'marketstack': bool(MSTACK),
        'elevenlabs': bool(ELEVENLABS_KEY),
        'alpha_vantage': bool(AV_KEY),
        'jwt_api': _HAS_JWT,
        'ai_models': _ai_models_now(),   # {fast, deep, gemini, nvidia} — antes 'ai_model' (uno que ya no mandaba)
        # Auditoría #15: SECRET_KEY por defecto = firmas falsificables. Solo el
        # booleano (nunca el valor); la UI/🩺 lo muestran como alerta.
        'secret_key_default': _secret_key_default(),
        'research': _research_brief(),           # R6: ¿puedo investigar ahora? (proveedores, cola, presupuesto)
        'ts': int(time.time()),
    })


def _research_brief():
    try:
        from research.health import health_brief
        return health_brief()
    except Exception as e:  # noqa: BLE001
        return {'ok': None, 'error': type(e).__name__}


# ----------------------------------------------------------------------------
# Diagnóstico EN VIVO — prueba real de cada integración (no solo bool(key))
# Cada check hace una llamada ligera y reporta ok / latencia / error real.
# NUNCA expone el valor de las keys; los errores se sanitizan.
# ----------------------------------------------------------------------------
_DIAG_CACHE = {'ts': 0.0, 'data': None}
_DIAG_TTL = 60  # segundos


def _diag_redact(text, limit=200):
    """Quita cualquier valor de key que pudiera aparecer en un mensaje de error:
    TODAS las env secretas (core.http.SECRET_ENV_NAMES: Gemini, NVIDIA, Alpaca,
    TRADE_PIN, KHIPU_ADMIN_SECRET, Tavily…) + los valores ya cargados aquí +
    patrones genéricos (key=/token=/apikey=/secret=, Bearer, x-goog-api-key…).
    Se redacta el texto COMPLETO y luego se trunca (antes se truncaba primero y
    un secreto cortado en el borde quedaba a medias sin tapar)."""
    return redact_secrets(text, extra=(CLAUDE, ELEVENLABS_KEY, FINNHUB, FMP, MSTACK, AV_KEY, SECRET_KEY,
                                       GEMINI_KEY, NVIDIA_KEY, ALPACA_KEY,
                                       ALPACA_SECRET, TRADE_PIN, KHIPU_ADMIN_SECRET),
                          limit=limit)


def _diag_card(es, en, fix=None, **fields):
    """Resultado de una tarjeta del 🩺 en los DOS idiomas (regla bilingüe): `detail` (ES, como siempre) +
    `detail_en`. Si hay un arreglo, va en `fix_es`/`fix_en` Y al final del detalle como « — QUÉ HACER: … » /
    « — WHAT TO DO: … » (el mismo formato que la voz): quien lea solo `detail` lo sigue viendo entero, y la
    tarjeta (app.html _diagTexts) lo quita del detalle al pintarlo aparte en «Qué hacer», sin repetirlo.
    `fix` = (es, en) o None. El resto de las claves (configured, ok, latency_ms, mode…) pasan tal cual."""
    out = dict(fields)
    if fix and fix[0] and fix[1]:
        out['detail'] = f'{es} — QUÉ HACER: {fix[0]}'
        out['detail_en'] = f'{en} — WHAT TO DO: {fix[1]}'
        out['fix_es'], out['fix_en'] = fix[0], fix[1]
    else:
        out['detail'], out['detail_en'] = es, en
    return out


def _diag_model_name(mid):
    """Nombre legible de un modelo de Claude: 'claude-sonnet-5-5' → 'Claude Sonnet 5.5' ·
    'claude-haiku-4-5-20251001' → 'Claude Haiku 4.5' · 'claude-3-5-sonnet-20241022' → 'Claude Sonnet 3.5'.
    Lo que no reconoce queda tal cual (nunca inventa)."""
    raw = re.sub(r'\[[^\]]*\]$', '', str(mid or '').strip())
    parts = [p for p in re.split(r'[-_]', raw.lower()) if p]
    if not parts or parts[0] != 'claude':
        return raw or 'Claude'
    fam = next((p for p in parts[1:] if p.isalpha()), '')
    if not fam:
        return raw
    nums = [p for p in parts[1:] if p.isdigit() and len(p) < 8]       # fuera la fecha (20251001)
    return 'Claude ' + fam.capitalize() + (' ' + '.'.join(nums) if nums else '')


def _diag_ai_route():
    """(es, en): el orden EFECTIVO de las IAs por nivel (core.ai.ai_route_state) en palabras simples, p. ej.
    «Profundo: Claude Sonnet 5.5 → Gemini → NVIDIA · Rápido: Gemini → Claude Haiku 4.5 → NVIDIA». Marca las
    que hoy se saltan (sin clave / en pausa) y si el orden lo fija una variable de Railway. Va ENTRE PARÉNTESIS a
    propósito: la tarjeta separa la pista « → …» del servidor en la primera flecha FUERA de paréntesis
    (app.html _diagHintAt) y las flechas del orden no son una pista. Solo nombres de modelo: nunca claves.
    Nunca lanza (sin estado → ('', ''))."""
    try:
        from core.ai import ai_route_state, circuit_open
        st = ai_route_state() or {}
    except Exception:  # noqa: BLE001 — el 🩺 jamás se rompe por esto
        return '', ''
    models = st.get('models') or {}

    def chain(tier, en):
        avail = set(st.get(tier + '_available') or [])
        names = []
        for p in st.get(tier) or []:
            name = (_diag_model_name(models.get(tier)) if p == 'claude'
                    else {'gemini': 'Gemini', 'nvidia': 'NVIDIA'}.get(p, str(p)))
            if p not in avail:
                try:
                    paused = circuit_open(p) is not None
                except Exception:  # noqa: BLE001
                    paused = False
                name += (' (paused)' if en else ' (en pausa)') if paused else (' (no key)' if en else ' (sin clave)')
            names.append(name)
        return ' → '.join(names) or '—'

    def label(tier, en):
        base = {('deep', False): 'Profundo', ('deep', True): 'Deep',
                ('fast', False): 'Rápido', ('fast', True): 'Fast'}[(tier, en)]
        src = st.get(tier + '_source')
        if src and src != 'default':
            base += f' (set by {src})' if en else f' (lo fija {src})'
        return base

    es = (f"(Orden de las IAs — {label('deep', False)}: {chain('deep', False)} · "
          f"{label('fast', False)}: {chain('fast', False)})")
    en = (f"(AI order — {label('deep', True)}: {chain('deep', True)} · "
          f"{label('fast', True)}: {chain('fast', True)})")
    return _diag_redact(es, limit=600), _diag_redact(en, limit=600)


def _diag_claude():
    from core.config import AI_MODEL_FAST, AI_MODEL_DEEP

    def _with_route(txt, route):
        if not route:
            return txt
        return f'{txt} {route}' if txt.endswith('.') else f'{txt} · {route}'

    if not CLAUDE:
        r_es, r_en = _diag_ai_route()
        return _diag_card(
            _with_route('ANTHROPIC_KEY no está en las variables del servidor (Railway). '
                        'Sin ella: Canvas IA, análisis de Khipu y el fallback del War-Room fallan.', r_es),
            _with_route('ANTHROPIC_KEY is not in the server variables (Railway). '
                        'Without it: AI Canvas, Khipu analysis and the War-Room fallback fail.', r_en),
            ('En Railway → tu servicio → Variables → añade ANTHROPIC_KEY con tu clave de console.anthropic.com. '
             'No hace falta tocar código.',
             'In Railway → your service → Variables → add ANTHROPIC_KEY with your key from console.anthropic.com. '
             'No code changes needed.'),
            configured=False, ok=False)
    t0 = time.time()
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=CLAUDE, timeout=20, max_retries=0)

        from core.ai import claude_ping_kwargs

        def _ping_model(mid):
            # pensamiento que ESE modelo acepta: Haiku 4.5 → disabled; Sonnet 5.5 → between_tools (disabled = 400);
            # Opus 5.5 / Fable → nada (no se puede apagar)
            _p = dict(model=mid, max_tokens=1, messages=[{'role': 'user', 'content': 'ping'}])
            try:
                m = client.messages.create(**claude_ping_kwargs(mid), **_p)
            except TypeError:
                m = client.messages.create(**_p)
            return m.model

        # Prueba explícita del modelo FAST y del DEEP (sonnet-5) por separado,
        # para diagnosticar exactamente cuál acepta la key.
        res, oks = {}, []
        for label, mid in (('fast', AI_MODEL_FAST), ('deep', AI_MODEL_DEEP)):
            try:
                res[label] = f'{mid} ✓ ({_ping_model(mid)})'
                oks.append(label)
            except Exception as e:  # noqa: BLE001
                res[label] = f'{mid} ✗ ({_diag_redact(e)})'
        detail = 'FAST: ' + res['fast'] + ' · DEEP: ' + res['deep']
        # Los dos niveles fallaron: la causa suele ser una sola (saldo, key, modelo retirado). Se dice una vez,
        # en claro, en los dos idiomas (fix_es/fix_en).
        fix = None if oks else _ai_error_fix(res['fast'] + ' ' + res['deep'],
                                             AI_MODEL_FAST, 'AI_MODEL_FAST/AI_MODEL_DEEP')
        # R1: el ping del 🩺 abre/cierra la pausa de Claude (los otros dos van por _complete_*)
        try:
            from core.ai import observe_diag
            observe_diag('claude', bool(oks), res['fast'] + ' ' + res['deep'])
        except Exception:  # noqa: BLE001
            pass
        r_es, r_en = _diag_ai_route()          # DESPUÉS del ping: refleja la pausa que acaba de abrir/cerrar
        return _diag_card(_with_route(detail, r_es), _with_route(detail, r_en), fix,
                          configured=True, ok=bool(oks), latency_ms=int((time.time() - t0) * 1000))
    except Exception as e:  # noqa: BLE001
        red = _diag_redact(e)
        r_es, r_en = _diag_ai_route()
        return _diag_card(_with_route('Key presente pero la API rechazó la llamada: ' + red, r_es),
                          _with_route('Key present but the API rejected the call: ' + red, r_en),
                          configured=True, ok=False, latency_ms=int((time.time() - t0) * 1000))


def _ai_error_fix(err_text, modelo, env_var):
    """(es, en) del arreglo para el error crudo de un proveedor de IA, o None si no hay pista reconocible
    (sin pista NO se inventa una explicación).

    Un '404'/'410' pelado no le dice a nadie qué hacer. Los proveedores RETIRAN
    modelos: pasó en sept-2026 con gemini-2.0-flash (404) y
    meta/llama-3.1-70b-instruct (410) a la vez, dejando la app sin respaldo.
    El arreglo nunca es tocar código — es cambiar la variable de entorno."""
    s = str(err_text)
    low = s.lower()
    if '404' in s or '410' in s or 'not found' in low or 'not_found' in low:
        return (f'El modelo «{modelo}» ya no existe en el proveedor (retirado). '
                f'Arreglo: pon {env_var} en Railway con un modelo vigente de su catálogo. '
                f'No hace falta desplegar.',
                f'The model “{modelo}” no longer exists at the provider (retired). '
                f'Fix: set {env_var} in Railway to a current model from its catalog. '
                f'No redeploy needed.')
    if '401' in s or '403' in s or 'api key' in low or 'unauthorized' in low:
        return ('La key parece inválida o sin permisos para ese modelo.',
                'The key looks invalid or has no permission for that model.')
    if '429' in s or 'quota' in low or 'rate' in low:
        return ('Límite de uso alcanzado (cuota o rate-limit). Espera o sube el plan.',
                'Usage limit reached (quota or rate limit). Wait or upgrade the plan.')
    if 'credit' in low or 'balance' in low or 'billing' in low:
        return ('Saldo agotado: recarga en la consola del proveedor.',
                'Out of credit: top up in the provider console.')
    return None


def _ai_error_hint(err_text, modelo, env_var):
    """Pista en español con el formato viejo (' → …'); '' si no hay pista. Ver `_ai_error_fix` (ES + EN)."""
    fx = _ai_error_fix(err_text, modelo, env_var)
    return (' → ' + fx[0]) if fx else ''


def _diag_gemini():
    if not GEMINI_KEY:
        return _diag_card(
            'GEMINI_KEY no está. (Opcional) Canal de respaldo de IA — Google Gemini.',
            'GEMINI_KEY is not set. (Optional) Backup AI channel — Google Gemini.',
            ('Opcional: crea una clave en aistudio.google.com y ponla en Railway → tu servicio → Variables → '
             'GEMINI_KEY.',
             'Optional: create a key at aistudio.google.com and put it in Railway → your service → Variables → '
             'GEMINI_KEY.'),
            configured=False, ok=False)
    t0 = time.time()
    try:
        txt, model = _complete_gemini('', 'ping', 1)
        return _diag_card(f'Key válida — {model} respondió.', f'Valid key — {model} answered.',
                          configured=True, ok=True, latency_ms=int((time.time() - t0) * 1000))
    except Exception as e:  # noqa: BLE001
        from core.config import GEMINI_MODEL
        red = _diag_redact(e)
        return _diag_card('Gemini rechazó la llamada: ' + red, 'Gemini rejected the call: ' + red,
                          _ai_error_fix(red, GEMINI_MODEL, 'GEMINI_MODEL'),
                          configured=True, ok=False, latency_ms=int((time.time() - t0) * 1000))


def _diag_nvidia():
    if not NVIDIA_KEY:
        return _diag_card(
            'NVIDIA_KEY no está. (Opcional) Canal de respaldo de IA — NVIDIA NIM (gratis para MVP).',
            'NVIDIA_KEY is not set. (Optional) Backup AI channel — NVIDIA NIM (free for the MVP).',
            ('Opcional: crea una clave en build.nvidia.com y ponla en Railway → tu servicio → Variables → '
             'NVIDIA_KEY.',
             'Optional: create a key at build.nvidia.com and put it in Railway → your service → Variables → '
             'NVIDIA_KEY.'),
            configured=False, ok=False)
    t0 = time.time()
    try:
        txt, model = _complete_nvidia('', 'ping', 1)
        return _diag_card(f'Key válida — {model} respondió.', f'Valid key — {model} answered.',
                          configured=True, ok=True, latency_ms=int((time.time() - t0) * 1000))
    except Exception as e:  # noqa: BLE001
        from core.config import NVIDIA_MODEL
        red = _diag_redact(e)
        return _diag_card('NVIDIA rechazó la llamada: ' + red, 'NVIDIA rejected the call: ' + red,
                          _ai_error_fix(red, NVIDIA_MODEL, 'NVIDIA_MODEL'),
                          configured=True, ok=False, latency_ms=int((time.time() - t0) * 1000))


def _diag_elevenlabs():
    """Tarjeta 🎙 del 🩺: diagnóstico ACCIONABLE (core/voice_agent.diagnose) —
    clave, plan/saldo, agente, LLM, modelo de voz, eventos, herramientas,
    prompt y overrides. `detail` (lo que pinta la tarjeta) trae los problemas
    y "QUÉ HACER" numerado; `detail_en`/`checks`/`fixes` para la UI bilingüe."""
    from core import voice_agent as _va
    t0 = time.time()
    try:
        d = _va.diagnose(ELEVENLABS_KEY, ELEVENLABS_AGENT_ID, http=requests,
                         expected_tools=[t['name'] for t in _bixby_client_tools()],
                         retired_tools=RETIRED_VOICE_TOOLS, prompt=BIXBY_SYSTEM_PROMPT, full=False)
        d['detail'] = _diag_redact(d.get('detail') or '', limit=2400)       # lleva "QUÉ HACER" numerado
        d['detail_en'] = _diag_redact(d.get('detail_en') or d.get('detail') or '', limit=2400)
        return d
    except Exception as e:  # noqa: BLE001 — el 🩺 jamás se rompe por la voz
        return {'configured': bool(ELEVENLABS_KEY), 'ok': False,
                'agent_configured': bool(ELEVENLABS_AGENT_ID),
                'latency_ms': int((time.time() - t0) * 1000),
                'detail': 'No se pudo revisar ElevenLabs: ' + _diag_redact(e),
                'detail_en': 'Could not check ElevenLabs: ' + _diag_redact(e)}


def _db_error_fix(err_text):
    """(es, en) del arreglo para un error de conexión a base de datos, o None.

    Mismo criterio que `_ai_error_fix`: un traceback de psycopg2 no le dice a
    nadie qué hacer. El caso real (sept-2026): DATABASE_URL apuntaba a
    'postgres.railway.internal' — el host de la red privada de Railway — pero
    el servicio Postgres ya no existía con ese nombre, así que el DNS interno
    no resolvía. Un texto literal en la variable envejece; una REFERENCIA
    (${{Postgres.DATABASE_URL}}) la resuelve Railway sola y nunca se queda
    obsoleta."""
    s = str(err_text).lower()
    if 'railway.internal' in s and ('translate host name' in s or 'name or service not known' in s):
        return ('El servicio de base de datos no existe con ese nombre en el proyecto. '
                'En Railway: crea el Postgres (+ New → Database) y pon la variable como '
                'REFERENCIA, no como texto: DATABASE_URL = ${{Postgres.DATABASE_URL}} '
                '(usa el nombre EXACTO que aparece en la tarjeta del servicio). '
                'Así Railway la resuelve sola y no vuelve a quedarse obsoleta.',
                'The database service does not exist with that name in the project. '
                'In Railway: create the Postgres (+ New → Database) and set the variable as a '
                'REFERENCE, not as text: DATABASE_URL = ${{Postgres.DATABASE_URL}} '
                '(use the EXACT name shown on the service card). '
                'That way Railway resolves it by itself and it never goes stale again.')
    if 'translate host name' in s or 'name or service not known' in s or 'nodename nor servname' in s:
        return ('El host de la base de datos no resuelve: el servidor no existe, cambió de '
                'nombre, o la instancia gratuita se borró por inactividad.',
                'The database host does not resolve: the server does not exist, was renamed, '
                'or the free instance was deleted for inactivity.')
    if 'password authentication failed' in s or 'authentication' in s:
        return ('El host responde pero las credenciales no son válidas: revisa usuario/contraseña.',
                'The host answers but the credentials are not valid: check user/password.')
    if 'does not exist' in s and 'database' in s:
        return ('El servidor responde pero esa base de datos no existe.',
                'The server answers but that database does not exist.')
    if 'connection refused' in s:
        return ('El host resuelve pero nadie escucha en ese puerto: ¿el servicio está apagado?',
                'The host resolves but nobody listens on that port: is the service turned off?')
    if 'timeout' in s or 'timed out' in s:
        return ('Tiempo de espera agotado: red o firewall entre la app y la base.',
                'Timed out: network or firewall between the app and the database.')
    return None


def _db_error_hint(err_text):
    """Pista en español con el formato viejo (' → …'); '' si no hay pista. Ver `_db_error_fix` (ES + EN)."""
    fx = _db_error_fix(err_text)
    return (' → ' + fx[0]) if fx else ''


def _diag_ontologia():
    """Ontología (Postgres, Fase 1 del roadmap): fuente única de verdad de
    objetos/vínculos con historia bitemporal. Feature opcional — si
    DATABASE_URL no está configurada, el resto de la app sigue igual."""
    try:
        from ontology.db import ontology_available
        if not ontology_available():
            return _diag_card(
                'Ontología no configurada (opcional). Añade el plugin de Postgres en '
                'Railway y DATABASE_URL para activar /api/ontology/*.',
                'Ontology not set up (optional). Add the Postgres plugin in '
                'Railway and DATABASE_URL to turn on /api/ontology/*.',
                configured=False, ok=True)
        # AUTO-REPARACIÓN: si la base arrancó DESPUÉS que la app (Railway lanza
        # los contenedores en paralelo), init_schema pudo fallar en el boot y el
        # esquema se quedó viejo — la app respondía 'column events.source_id
        # does not exist'. Detectarlo aquí y repararlo convierte el botón
        # "Re-probar" del panel en el arreglo, sin redesplegar.
        from ontology.db import init_schema, schema_outdated
        faltantes = schema_outdated()
        if faltantes:
            reparado = init_schema()
            if not reparado or schema_outdated():
                cols = ', '.join(faltantes)
                return _diag_card(
                    f'Esquema desactualizado: faltan {cols}. '
                    'Se intentó reparar automáticamente y no se pudo.',
                    f'Outdated schema: missing {cols}. '
                    'An automatic repair was attempted and failed.',
                    ('Reinicia el servicio en Railway (Deployments → Restart) y luego pulsa ↻ Re-probar.',
                     'Restart the service in Railway (Deployments → Restart), then press ↻ Re-test.'),
                    configured=True, ok=False)
            log.warning('Esquema de la ontología reparado en caliente: %s', faltantes)

        from ontology.db import session_scope
        from ontology.models import ObjectRecord, LinkRecord, Event
        with session_scope() as s:
            n_obj = s.query(ObjectRecord).count()
            n_link = s.query(LinkRecord).count()
            n_ev = s.query(Event).count()
            last_ev = s.query(Event).order_by(Event.recorded_at.desc()).first()
        lineage = lineage_en = ''
        if last_ev:
            _when = last_ev.recorded_at.strftime("%Y-%m-%d %H:%M UTC")
            lineage = f' · último evento: {_when} ({last_ev.source})'
            lineage_en = f' · last event: {_when} ({last_ev.source})'
        hot_es, hot_en, hot = _diag_hot_views()
        return _diag_card(f'Ontología activa — {n_obj} objetos, {n_link} vínculos, {n_ev} eventos.{lineage}{hot_es}',
                          f'Ontology active — {n_obj} objects, {n_link} links, {n_ev} events.{lineage_en}{hot_en}',
                          configured=True, ok=True, hot_views=hot)
    except Exception as e:  # noqa: BLE001
        red = _diag_redact(e)
        return _diag_card('Ontología configurada pero no conecta: ' + red,
                          'Ontology is set up but does not connect: ' + red,
                          _db_error_fix(red), configured=True, ok=False)


def _diag_gobernanza():
    """Tarjeta 🩺 del registro de gobernanza (paso 9) y de la cadena del libro (paso 7): release vigente, si falta
    ratificarlo con PIN, variables de entorno que ya no mandan (D2) y si el dinero real está bloqueado."""
    try:
        from core import governance
        st = governance.status()
        es, en = governance.explain('es'), governance.explain('en')
        ok = not st['env_warnings'] and not st['db_error'] and not st.get('repo_fallback')
        fix = None
        if st.get('repo_fallback'):
            fix = ('propón un release que incluya ' + ', '.join(sorted(st['repo_fallback'])) + ' y apruébalo con tu '
                   'PIN (hasta entonces sus números salen del repositorio y cada decisión lo anota).',
                   'propose a release that includes ' + ', '.join(sorted(st['repo_fallback'])) + ' and approve it '
                   'with your PIN (until then its numbers come from the repository and every decision notes it).')
        for w in st['env_warnings']:
            es += ' ' + w['es']
            en += ' ' + w['en']
        if st['db_error']:
            es += f" Error al leer el release de la base: {st['db_error'][:120]} (sigue el anterior)."
            en += f" Error reading the release from the database: {st['db_error'][:120]} (the previous one stays)."
        _props = [p for p in (st.get('proposals') or []) if p.get('newer')]
        if _props:   # paso 12: versiones disponibles que SOLO entran en vigor con el PIN de Fabrizio
            _names = ', '.join(f"{p['id']} {p['semver']}" for p in _props[:4])
            es += f' Disponible para activar con tu PIN: {_names} (mira «¿Qué cambia?» abajo).'
            en += f' Available to activate with your PIN: {_names} (see "What changes?" below).'
        if st['needs_ratification'] and fix is None:
            fix = ('ratifica el release una vez: 🩺 → Gobernanza → «Ratificar» con tu PIN (no bloquea nada).',
                   'ratify the release once: 🩺 → Governance → "Ratify" with your PIN (it blocks nothing).')
        chain = None
        try:
            from ontology.db import ontology_available
            if ontology_available():
                from core import ledger
                chain = ledger.chain_state()
                if chain.get('broken'):
                    ok = False
                    es += ' CADENA DEL LIBRO ROTA: el dinero real está bloqueado hasta reconocerla con PIN.'
                    en += ' LEDGER CHAIN BROKEN: real money is blocked until it is acknowledged with the PIN.'
                    fix = ('revisa qué cambió (🩺 → Libro → Verificar) y reconócelo con tu PIN: POST /api/ledger/chain_ack.',
                           'check what changed (🩺 → Ledger → Verify) and acknowledge it with your PIN: '
                           'POST /api/ledger/chain_ack.')
        except Exception:  # noqa: BLE001
            chain = None
        try:   # paso 10: puertas en sombra (modo, reglas, avisos desde el arranque)
            import core.gates as _gates
            gs = _gates.status()
            n_warn = sum((gs.get('stats') or {}).get('by_rule', {}).values())
            if not gs.get('available') and gs.get('mode') != 'off':
                ok = False
                es += f" Puertas NO disponibles: {gs.get('error') or 'sin IR'}."
                en += f" Gates UNAVAILABLE: {gs.get('error') or 'no IR'}."
            else:
                _gm_es = {'shadow': 'SOMBRA', 'block': 'BLOQUEO (ontología)'}.get(gs['mode'], 'APAGADAS (KHIPU_GATES=off)')
                _gm_en = {'shadow': 'SHADOW', 'block': 'BLOCKING (ontology)'}.get(gs['mode'], 'OFF (KHIPU_GATES=off)')
                es += f" Puertas en {_gm_es}: {gs.get('rules', 0)} reglas, {n_warn} aviso(s) desde el arranque."
                en += f" Gates in {_gm_en}: {gs.get('rules', 0)} rules, {n_warn} warning(s) since start."
        except Exception:  # noqa: BLE001
            gs = None
        g3 = _diag_g3_bullets()            # pasos 11, 22, 24 y 26: Puertas 7 días · guardia · repetición · retención
        es += g3['es']
        en += g3['en']
        try:   # E0.2 (lote J): MATRIX_ENGINE=dense con más de DENSE_MAX_NODES nodos no se obedece (mismos números)
            from matrix import engine as _ME
            _dr = _ME.dense_refused()
            if _dr:
                ok = False
                es += ' ' + _dr['es']
                en += ' ' + _dr['en']
        except Exception:  # noqa: BLE001
            _dr = None
        if (g3.get('replay') or {}).get('differs'):          # paso 24: una decisión ya no se repite igual → rojo
            ok = False
            fix = fix or ('abre 🩺 → 📋 Registro → ⚖ Auditoría: arriba, en «Distintas en la última muestra», pulsa «Repetir» '
                          'para ver qué campo cambió (o el código que la calcula cambió o algo del registro no cuadra).',
                          'open 🩺 → 📋 Log → ⚖ Audit: at the top, under "Different in the last sample", press "Replay" to '
                          'see which field changed (either the code that computes it changed or something in the record '
                          'does not add up).')
        return _diag_card(es, en, fix, configured=True, ok=ok, release=st['release_hash'][:16],
                          gates_7d=g3.get('gates_7d'), guard=g3.get('guard'), retention=g3.get('retention'),
                          replay=g3.get('replay'),
                          gates_mode=(gs or {}).get('mode'),
                          semver=st['semver'], label=st['label'], ratified=st['ratified'],
                          env_warnings=[w['env'] for w in st['env_warnings']],
                          chain_broken=bool(chain and chain.get('broken')))
    except Exception as e:  # noqa: BLE001
        return _diag_card('Registro de gobernanza no disponible: ' + type(e).__name__,
                          'Governance registry unavailable: ' + type(e).__name__, configured=True, ok=False)


def _diag_g3_bullets():
    """Viñetas de la tarjeta ⚖ Gobernanza (sin tarjeta nueva): «Puertas» = 7 días de avisos en sombra por regla y
    cuántas escrituras se habrían bloqueado con policy.gates@2.0.0 (paso 11); «Guardia» = cambios sin decisión del
    libro en 7 días y el camino del código (paso 22); «Retención» = última purga (paso 26). Nunca lanza."""
    out = {'es': '', 'en': ''}
    try:
        from ontology.db import ontology_available
        if not ontology_available():
            return out
    except Exception:  # noqa: BLE001
        return out
    try:
        from core.gates import report as _grep
        g = _grep.shadow_summary(7)
        if g.get('available'):
            top = ', '.join(f"{r['rule'].replace('khr:', '')} ×{r['n']}" for r in g['rules'][:4]) or '—'
            out['es'] += (f" • Puertas (7 días): {g['total']} aviso(s) en sombra; con la versión 2.0.0 (bloqueo) se "
                          f"habrían rechazado {g['decisions_would_block']} escritura(s). Más frecuentes: {top}.")
            out['en'] += (f" • Gates (7 days): {g['total']} shadow warning(s); with version 2.0.0 (blocking) "
                          f"{g['decisions_would_block']} write(s) would have been rejected. Most frequent: {top}.")
            out['gates_7d'] = {k: g[k] for k in ('total', 'would_block', 'decisions_would_block')} | {
                'rules': g['rules'][:12]}
    except Exception:  # noqa: BLE001
        pass
    try:
        from core import ledger_guard as _lg
        gd = _lg.status()
        if gd.get('available'):
            by = ', '.join(f"{r['table']} {r['op']} ×{r['n']}" for r in gd['by_table'][:4]) or '—'
            mode_es = 'AVISO' if (gd.get('mode') or 'warn') == 'warn' else 'BLOQUEO'
            mode_en = 'WARN' if (gd.get('mode') or 'warn') == 'warn' else 'ENFORCE'
            out['es'] += (f" • Guardia «sin decisión no hay cambio» en {mode_es}: {gd['total']} cambio(s) sin decisión "
                          f"en 7 días ({by}); disparadores {gd.get('triggers')}/{gd.get('triggers_expected')}.")
            out['en'] += (f" • \"No decision, no change\" guard in {mode_en}: {gd['total']} change(s) without a "
                          f"decision in 7 days ({by}); triggers {gd.get('triggers')}/{gd.get('triggers_expected')}.")
            out['guard'] = gd
    except Exception:  # noqa: BLE001
        pass
    try:   # paso 24: muestra nocturna de replays (¿las decisiones de ayer se repiten idénticas?)
        from core import replay as _rp
        rs = _rp.status()
        last = rs.get('last') or {}
        cn = last.get('counts') or {}
        when = (last.get('at') or '')[:16].replace('T', ' ') or None
        if when:
            out['es'] += (f" • Repetición (muestra del {when}): {last.get('sampled', 0)} decisiones — "
                          f"{cn.get('identical', 0)} idénticas, {cn.get('differs', 0)} distintas, "
                          f"{cn.get('not_replayable', 0)} no repetibles (IA o datos en vivo).")
            out['en'] += (f" • Replay (sample of {when}): {last.get('sampled', 0)} decisions — "
                          f"{cn.get('identical', 0)} identical, {cn.get('differs', 0)} different, "
                          f"{cn.get('not_replayable', 0)} not replayable (AI or live data).")
        else:
            out['es'] += ' • Repetición: la primera muestra nocturna aún no corrió (⚖ Auditoría deja repetir una a mano).'
            out['en'] += ' • Replay: the first nightly sample has not run yet (⚖ Audit lets you replay one by hand).'
        out['replay'] = rs
    except Exception:  # noqa: BLE001
        pass
    try:
        from core import retention as _ret
        rt = _ret.status()
        last = rt.get('last') or {}
        when = (last.get('at') or '')[:16].replace('T', ' ') or None
        out['es'] += (f" • Retención (D3): chat y qué-pasaría-si {rt['params']['standard_days']} días, lo demás para "
                      f"siempre; última purga {when or 'aún no'}"
                      f"{' (' + str(last.get('purged', 0)) + ' contenidos vaciados, huellas intactas)' if when else ''}; "
                      f"pendientes {rt.get('pending') if rt.get('pending') is not None else '—'}"
                      f"{' (' + str(rt['protected']) + ' viejos protegidos: algo vigente los cita)' if rt.get('protected') else ''}.")
        out['en'] += (f" • Retention (D3): chat and what-if {rt['params']['standard_days']} days, the rest forever; "
                      f"last purge {when or 'not yet'}"
                      f"{' (' + str(last.get('purged', 0)) + ' contents emptied, fingerprints intact)' if when else ''}; "
                      f"pending {rt.get('pending') if rt.get('pending') is not None else '—'}"
                      f"{' (' + str(rt['protected']) + ' old ones protected: something in force cites them)' if rt.get('protected') else ''}.")
        out['retention'] = rt
    except Exception:  # noqa: BLE001
        pass
    return out


def _diag_hot_views():
    """Línea del 🩺 para las vistas rápidas (INFRA_OPERATIVA paso 4): generación, edad, ms de construcción,
    atraso y registro append-only. (texto ES, texto EN, dict)."""
    try:
        from core import ledger_ddl
        from core.hotviews import builder, registry
        g = registry.generation()
        st = builder.state()
        ao = 'events append-only' if ledger_ddl.STATE.get('ready') else 'events SIN disparador append-only'
        ao_en = 'events append-only' if ledger_ddl.STATE.get('ready') else 'events WITHOUT append-only trigger'
        if g is None:
            return (f' · Vistas rápidas: preparándose · {ao}', f' · Fast views: warming up · {ao_en}',
                    {'warming': True, 'builder': st, 'append_only': ledger_ddl.STATE.get('ready')})
        lag_v, stale = registry.lag(g)
        age = int(time.time() - g.built_ts)
        ms = (g.build_ms or {}).get('total')
        es = (f' · Vistas rápidas: {g.id}, edad {age} s, construcción {ms} ms'
              f'{", ATRASADA " + str(lag_v) + " versión(es)" if lag_v else ""} · {ao}')
        en = (f' · Fast views: {g.id}, age {age} s, build {ms} ms'
              f'{", BEHIND by " + str(lag_v) + " version(s)" if lag_v else ""} · {ao_en}')
        if st.get('last_error') and (st.get('last_error_at') or 0) > g.built_ts:
            es += f' · último error: {st["last_error"][:80]}'
            en += f' · last error: {st["last_error"][:80]}'
        return es, en, {'generation': g.id, 'graph_version': g.graph_version, 'age_s': age, 'build_ms': g.build_ms,
                        'lag_versions': lag_v, 'stale': stale, 'source': g.source,
                        'append_only': ledger_ddl.STATE.get('ready')}
    except Exception as e:  # noqa: BLE001
        return '', '', {'error': type(e).__name__}


def _diag_grafo():
    """Grafo Temporal: siempre NATIVO. La memoria temporal vive en Postgres (la ontología bitemporal) y en el
    navegador; Neo4j se retiró el 2026-10-13 (decisión #6) y no hay otra base que configurar ni probar."""
    return _diag_card(
        'Grafo de Conocimiento Temporal en modo NATIVO: la memoria temporal vive en Postgres (la ontología con su '
        'historia) y en el navegador. No necesita otra base de datos.',
        'Temporal Knowledge Graph in NATIVE mode: the temporal memory lives in Postgres (the ontology and its '
        'history) and in the browser. No other database needed.',
        configured=True, ok=True, store='native')


def _diag_alpaca():
    """Bróker: configurado, alcanzable y — LO MÁS IMPORTANTE para un usuario no
    técnico — en qué modo está: PAPEL (simulado) o REAL. Auditoría Track D: era
    el gap de seguridad/UX más grande (no había forma de verlo dentro de la app)."""
    mode = 'paper' if 'paper-api' in ALPACA_BASE else 'live'
    if not ALPACA_KEY:
        return _diag_card(
            'ALPACA_KEY sin configurar — el bróker simulado está apagado.',
            'ALPACA_KEY not set — the simulated broker is off.',
            ('Opcional: crea una cuenta de papel (simulada, gratis) en alpaca.markets y pon ALPACA_KEY y '
             'ALPACA_SECRET en Railway → tu servicio → Variables.',
             'Optional: create a paper (simulated, free) account at alpaca.markets and put ALPACA_KEY and '
             'ALPACA_SECRET in Railway → your service → Variables.'),
            configured=False, ok=False, mode=mode)
    try:
        r = requests.get(f'{ALPACA_BASE}/v2/account', headers=_alpaca_hdrs(), timeout=8)
        ok = r.status_code == 200
        if ok and mode == 'paper':
            es, en = ('Cuenta PAPEL (simulada) conectada — sin dinero real.',
                      'PAPER (simulated) account connected — no real money.')
        elif ok:
            es, en = ('⚠ Cuenta REAL conectada — las órdenes mueven dinero de verdad.',
                      '⚠ REAL account connected — orders move real money.')
        else:
            es, en = f'Alpaca respondió HTTP {r.status_code}.', f'Alpaca answered HTTP {r.status_code}.'
        fix = None
        if r.status_code in (401, 403):
            fix = ('Revisa ALPACA_KEY y ALPACA_SECRET en Railway → tu servicio → Variables (las claves de papel '
                   'solo sirven con la dirección de papel y las reales con la real).',
                   'Check ALPACA_KEY and ALPACA_SECRET in Railway → your service → Variables (paper keys only '
                   'work with the paper address, live keys with the live one).')
        return _diag_card(es, en, fix, configured=True, ok=ok, mode=mode)
    except Exception as e:  # noqa: BLE001
        red = _diag_redact(e, limit=100)       # antes str(e) crudo: podía arrastrar una cabecera o URL con clave
        return _diag_card(f'Alpaca inalcanzable: {red}', f'Alpaca unreachable: {red}',
                          configured=True, ok=False, mode=mode)


def _diag_finnhub():
    if not FINNHUB:
        return _diag_card(
            'FINNHUB_KEY no está. Los precios en vivo del terminal no cargarán.',
            'FINNHUB_KEY is not set. Live prices in the terminal will not load.',
            ('Crea una clave gratis en finnhub.io y ponla en Railway → tu servicio → Variables → FINNHUB_KEY.',
             'Create a free key at finnhub.io and put it in Railway → your service → Variables → FINNHUB_KEY.'),
            configured=False, ok=False)
    t0 = time.time()
    try:
        r = requests.get(f'https://finnhub.io/api/v1/quote?symbol=AAPL&token={FINNHUB}', timeout=6)
        lat = int((time.time() - t0) * 1000)
        if r.ok:
            c = (r.json() or {}).get('c')
            if isinstance(c, (int, float)) and c > 0:
                return _diag_card(f'Key válida — cotización AAPL ${c} OK.', f'Valid key — AAPL quote ${c} OK.',
                                  configured=True, ok=True, latency_ms=lat)
            return _diag_card(
                'Key responde pero sin datos (¿límite de plan agotado?).',
                'The key answers but with no data (plan limit used up?).',
                ('Espera unos minutos y pulsa ↻ Re-probar; si sigue igual, revisa tu plan en finnhub.io. '
                 'Mientras tanto los precios vienen de Yahoo.',
                 'Wait a few minutes and press ↻ Re-test; if nothing changes, check your plan at finnhub.io. '
                 'Meanwhile prices come from Yahoo.'),
                configured=True, ok=False, latency_ms=lat)
        fix = None
        if r.status_code in (401, 403):
            fix = ('Revisa FINNHUB_KEY en Railway → tu servicio → Variables (cópiala de nuevo desde finnhub.io).',
                   'Check FINNHUB_KEY in Railway → your service → Variables (copy it again from finnhub.io).')
        elif r.status_code == 429:
            fix = ('Límite de uso alcanzado: espera un minuto y pulsa ↻ Re-probar. '
                   'Mientras tanto los precios vienen de Yahoo.',
                   'Usage limit reached: wait a minute and press ↻ Re-test. Meanwhile prices come from Yahoo.')
        return _diag_card(f'Finnhub HTTP {r.status_code} — key inválida o rate-limited.',
                          f'Finnhub HTTP {r.status_code} — invalid key or rate-limited.',
                          fix, configured=True, ok=False, latency_ms=lat)
    except Exception as e:  # noqa: BLE001
        red = _diag_redact(e)
        return _diag_card('No se pudo contactar Finnhub: ' + red, 'Could not reach Finnhub: ' + red,
                          configured=True, ok=False, latency_ms=int((time.time() - t0) * 1000))


def _diag_fmp():
    """FMP se PRUEBA de verdad (perfil de AAPL): antes la barra de salud decía
    "listo" solo porque la key existía, aunque el plan devolviera 402."""
    if not FMP:
        return _diag_card(
            'FMP_KEY no está. Estados financieros y dossier usan Yahoo/AlphaVantage.',
            'FMP_KEY is not set. Financial statements and the dossier use Yahoo/AlphaVantage.',
            ('Opcional: crea una clave en financialmodelingprep.com y ponla en Railway → tu servicio → '
             'Variables → FMP_KEY.',
             'Optional: create a key at financialmodelingprep.com and put it in Railway → your service → '
             'Variables → FMP_KEY.'),
            configured=False, ok=False)
    t0 = time.time()
    try:
        r = requests.get(f'https://financialmodelingprep.com/stable/profile?symbol=AAPL&apikey={FMP}', timeout=8)
        lat = int((time.time() - t0) * 1000)
        if r.ok:
            body = r.json() or []
            row = body[0] if isinstance(body, list) and body else (body if isinstance(body, dict) else {})
            name = row.get('companyName') or row.get('symbol')
            if name:
                return _diag_card(f'Key válida — perfil de AAPL ({name}) OK.', f'Valid key — AAPL profile ({name}) OK.',
                                  configured=True, ok=True, latency_ms=lat)
            return _diag_card('Key responde pero sin datos (¿plan sin cobertura?).',
                              'The key answers but with no data (plan without coverage?).',
                              configured=True, ok=False, latency_ms=lat)
        if r.status_code == 402:
            hint, hint_en = ' — plan sin acceso a este endpoint (402).', ' — the plan has no access to this endpoint (402).'
            fix = ('Es normal en el plan gratuito: los estados financieros salen de Yahoo/AlphaVantage. '
                   'Para usar FMP aquí, sube de plan en financialmodelingprep.com.',
                   'Normal on the free plan: financial statements come from Yahoo/AlphaVantage. '
                   'To use FMP here, upgrade the plan at financialmodelingprep.com.')
        else:
            hint, hint_en = ' — key inválida o rate-limited.', ' — invalid key or rate-limited.'
            fix = (('Revisa FMP_KEY en Railway → tu servicio → Variables (cópiala de nuevo desde '
                    'financialmodelingprep.com).',
                    'Check FMP_KEY in Railway → your service → Variables (copy it again from '
                    'financialmodelingprep.com).') if r.status_code in (401, 403) else None)
        return _diag_card(f'FMP HTTP {r.status_code}{hint}', f'FMP HTTP {r.status_code}{hint_en}', fix,
                          configured=True, ok=False, latency_ms=lat)
    except Exception as e:  # noqa: BLE001
        red = _diag_redact(e)
        return _diag_card('No se pudo contactar FMP: ' + red, 'Could not reach FMP: ' + red,
                          configured=True, ok=False, latency_ms=int((time.time() - t0) * 1000))


def _diag_yahoo():
    """Yahoo (sin key) es el respaldo de precios de TODO el catálogo y la única
    fuente de las bolsas fuera de EE.UU.: se prueba con el chart de NVDA."""
    t0 = time.time()
    try:
        r = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/NVDA',
                         params={'interval': '1d', 'range': '5d'},
                         headers={'User-Agent': 'Mozilla/5.0 (compatible; Khipu/1.0)'}, timeout=8)
        lat = int((time.time() - t0) * 1000)
        if r.ok:
            res = (((r.json() or {}).get('chart') or {}).get('result') or [None])[0] or {}
            px = (res.get('meta') or {}).get('regularMarketPrice')
            if isinstance(px, (int, float)) and px > 0:
                return _diag_card(
                    f'Yahoo responde — cotización NVDA ${px} OK (sin key, cubre todas las bolsas).',
                    f'Yahoo answers — NVDA quote ${px} OK (no key needed, covers every exchange).',
                    configured=True, ok=True, latency_ms=lat)
            return _diag_card('Yahoo responde pero sin precio para NVDA.', 'Yahoo answers but has no price for NVDA.',
                              configured=True, ok=False, latency_ms=lat)
        fix = None
        if r.status_code in (403, 429):
            fix = ('Espera unos minutos y pulsa ↻ Re-probar: Yahoo suele levantar el bloqueo solo (no usa clave).',
                   'Wait a few minutes and press ↻ Re-test: Yahoo usually lifts the block by itself (it uses no key).')
        return _diag_card(f'Yahoo HTTP {r.status_code} — puede estar bloqueando al servidor (rate limit).',
                          f'Yahoo HTTP {r.status_code} — it may be blocking the server (rate limit).',
                          fix, configured=True, ok=False, latency_ms=lat)
    except Exception as e:  # noqa: BLE001
        red = _diag_redact(e)
        return _diag_card('No se pudo contactar Yahoo: ' + red, 'Could not reach Yahoo: ' + red,
                          configured=True, ok=False, latency_ms=int((time.time() - t0) * 1000))


def _diag_research_fix(rh):
    """(es, en) de «Qué hacer» para la tarjeta 🔬 cuando la investigación NO puede correr, o None."""
    provs = rh.get('providers') or {}
    budget = ((rh.get('budget') or {}).get('research') or {})
    if provs and not any((v or {}).get('configured') for v in provs.values()):
        return ('Añade al menos una clave de IA en Railway → tu servicio → Variables: ANTHROPIC_KEY, GEMINI_KEY '
                'o NVIDIA_KEY.',
                'Add at least one AI key in Railway → your service → Variables: ANTHROPIC_KEY, GEMINI_KEY '
                'or NVIDIA_KEY.')
    if provs and not any((v or {}).get('available') for v in provs.values()):
        return ('Mira las tarjetas de IA de arriba: cada una dice por qué está en pausa y cómo arreglarlo. '
                'Luego pulsa ↻ Re-probar.',
                'Look at the AI cards above: each one says why it is paused and how to fix it. '
                'Then press ↻ Re-test.')
    if budget.get('exhausted'):
        return ('Espera a mañana (00:05 UTC) o sube RESEARCH_DAILY_BUDGET_USD en Railway → tu servicio → Variables.',
                'Wait until tomorrow (00:05 UTC) or raise RESEARCH_DAILY_BUDGET_USD in Railway → your service → '
                'Variables.')
    return None


@app.route('/api/ai/debug')
@rate_limit(limit=20, window=300)
def ai_debug():
    """Depuración: ejecuta _ai_complete con un prompt real (tier configurable) y
    reporta AI_ORDER, los modelos resueltos y el error/modelo real — sin exponer
    claves. Para diagnosticar por qué la sim usa NVIDIA en vez de Sonnet 5."""
    from core import ai as _ai
    from core.config import AI_ORDER as _ORDER, AI_MODEL_FAST as _F, AI_MODEL_DEEP as _D
    tier = 'deep' if request.args.get('tier') == 'deep' else 'fast'
    # el orden que la cascada USA de verdad en este nivel (AI_ORDER_FAST/_DEEP > AI_ORDER…; el profundo ignora
    # AI_ORDER) — antes se mostraba la variable vieja tal cual y engañaba justo en este diagnóstico
    out = {'ai_order': _ai.provider_order(tier), 'ai_order_env': _ORDER, 'routing': _ai.ai_route_state(),
           'model_fast': _F, 'model_deep': _D, 'tier': tier}
    # 1) el motor completo (con cascada)
    try:
        txt, model = _ai._ai_complete('Eres un analista. Responde SOLO JSON.',
                                      'Devuelve {"ok":true,"n":3} y una frase de análisis.',
                                      max_tokens=900, tier=tier)
        out['cascade'] = {'model': model, 'text_len': len(txt or ''), 'preview': (txt or '')[:120]}
    except Exception as e:  # noqa: BLE001
        out['cascade'] = {'error': _diag_redact(e)}
    # 2) Claude directo (aísla si el problema es Claude o la cascada)
    try:
        txt2, model2 = _ai._complete_claude('Eres un analista. Responde SOLO JSON.',
                                            'Devuelve {"ok":true,"n":3} y una frase de análisis.',
                                            max_tokens=900, tier=tier)
        out['claude_direct'] = {'model': model2, 'text_len': len(txt2 or ''), 'preview': (txt2 or '')[:120]}
    except Exception as e:  # noqa: BLE001
        out['claude_direct'] = {'error': _diag_redact(e)}
    return jsonify(out)


def _security_warnings():
    """Avisos de postura de seguridad para 🩺 (bilingües, sin valores secretos)."""
    out = []
    if _secret_key_default():
        prod = _insecure_prod_secret()
        out.append({
            'code': 'secret_key_default', 'severity': 'critical' if prod else 'warning',
            'es': ('🚨 SECRET_KEY es la de por defecto (pública). Cualquiera puede falsificar lo que se firma con '
                   'ella. Railway → tu servicio → Variables → añade SECRET_KEY con un texto largo y aleatorio.'
                   + (' La conexión de IAs por OAuth (MCP) queda desactivada hasta que la cambies.' if prod else '')),
            'en': ('🚨 SECRET_KEY is the default (public) one. Anyone can forge what is signed with it. '
                   'Railway → your service → Variables → add SECRET_KEY with a long random string.'
                   + (' AI connections via OAuth (MCP) stay disabled until you change it.' if prod else '')),
        })
    pin = os.getenv('TRADE_PIN', '')
    if not pin:
        out.append({'code': 'trade_pin_missing', 'severity': 'info',
                    'es': 'TRADE_PIN no está configurado: el trading y el corretaje quedan deshabilitados.',
                    'en': 'TRADE_PIN is not set: trading and brokerage are disabled.'})
    elif len(pin) < 8:
        out.append({'code': 'trade_pin_weak', 'severity': 'warning',
                    'es': 'TRADE_PIN es corto (< 8 caracteres): usa uno más largo en Railway.',
                    'en': 'TRADE_PIN is short (< 8 characters): use a longer one in Railway.'})
    if not _house_trading_enabled():
        out.append({'code': 'trading_halted', 'severity': 'info',
                    'es': 'Interruptor general APAGADO (BROKERAGE_TRADING_ENABLED=off): no se envía ninguna orden '
                          '(tampoco cierres). Para cerrar una posición en una emergencia usa el panel de Alpaca.',
                    'en': 'Master switch OFF (BROKERAGE_TRADING_ENABLED=off): no orders are sent (closes '
                          'included). To close a position in an emergency use the Alpaca dashboard.'})
    if FINNHUB and not (os.getenv('FINNHUB_WS_KEY') or '').strip():
        # Auditoría #14 (residual): /api/ws-key entrega la key al navegador; un
        # cliente que falsifique Sec-Fetch-Site también la obtiene.
        out.append({'code': 'finnhub_ws_key_missing', 'severity': 'warning',
                    'es': 'El WebSocket de precios usa la FINNHUB_KEY del servidor: alguien que imite al navegador '
                          'podría obtenerla. Crea una segunda key gratis en finnhub.io y ponla en Railway como '
                          'FINNHUB_WS_KEY (si se filtra, la cambias sin tocar la del servidor).',
                    'en': 'The price WebSocket uses the server FINNHUB_KEY: someone imitating the browser could '
                          'obtain it. Create a second free key at finnhub.io and set it in Railway as '
                          'FINNHUB_WS_KEY (if it leaks, rotate it without touching the server key).'})
    return out


@app.route('/api/diagnostics')
@rate_limit(limit=20, window=300)
def diagnostics():
    now = time.time()
    fresh = request.args.get('fresh') == '1'
    if not fresh and _DIAG_CACHE['data'] and (now - _DIAG_CACHE['ts'] < _DIAG_TTL):
        out = dict(_DIAG_CACHE['data'])
        out['cached'] = True
        return jsonify(_diag_view(out))

    services = {
        'claude':     _diag_claude(),
        'gemini':     _diag_gemini(),
        'nvidia':     _diag_nvidia(),
        'elevenlabs': _diag_elevenlabs(),
        'finnhub':    _diag_finnhub(),
        'yahoo':      _diag_yahoo(),
        'fmp':        _diag_fmp(),
        'grafo':      _diag_grafo(),
        'ontologia':  _diag_ontologia(),
        'gobernanza': _diag_gobernanza(),
        'alpaca':     _diag_alpaca(),
    }
    # R1: proveedores de IA en pausa por error definitivo (sin saldo, clave, modelo)
    try:
        from core.ai import ai_circuit_state
        for _p, _st in ai_circuit_state().items():
            if _p in services:
                services[_p]['circuit'] = _st
                if _st.get('open'):
                    _hhmm = str(_st.get('until_iso') or '')[11:16]
                    _en = str(services[_p].get('detail_en') or services[_p].get('detail') or '')
                    services[_p]['detail'] = (f"EN PAUSA hasta {_hhmm} UTC: {_st['reason_es']} "
                                              f"(la cascada lo salta; el ping de arriba lo reactiva si vuelve a responder). "
                                              + str(services[_p].get('detail') or ''))
                    services[_p]['detail_en'] = (f"PAUSED until {_hhmm} UTC: {_st.get('reason_en') or _st['reason_es']} "
                                                 f"(the cascade skips it; the ping above turns it back on if it answers "
                                                 f"again). " + _en)
    except Exception:  # noqa: BLE001
        pass
    # Finnhub en pausa por cuota (HTTP 429) → se dice tal cual en 🩺
    try:
        from core.quotes import finnhub_circuit_state
        _fc = finnhub_circuit_state()
        if _fc['paused'] and services['finnhub'].get('configured'):
            services['finnhub']['quota'] = True
            _en = str(services['finnhub'].get('detail_en') or services['finnhub'].get('detail') or '')
            services['finnhub']['detail'] = (f"Cuota agotada (HTTP 429): Finnhub en pausa {_fc['seconds_left']} s; "
                                             'los precios vienen de Yahoo mientras tanto. '
                                             + str(services['finnhub'].get('detail') or ''))
            services['finnhub']['detail_en'] = (f"Quota used up (HTTP 429): Finnhub paused for {_fc['seconds_left']} s; "
                                                'prices come from Yahoo meanwhile. ' + _en)
    except Exception:  # noqa: BLE001
        pass
    # Secundarias: solo presencia (no gastamos llamadas externas extra)
    _extra_names = [n for n, v in (('MarketStack', MSTACK), ('AlphaVantage', AV_KEY)) if v]
    if _extra_names:
        services['market_extra'] = _diag_card('Respaldo EOD/histórico activo: ' + ', '.join(_extra_names) + '.',
                                              'EOD/historical backup active: ' + ', '.join(_extra_names) + '.',
                                              configured=True, ok=True)
    else:
        services['market_extra'] = _diag_card(
            'Sin respaldo EOD (MarketStack/AlphaVantage): los precios dependen de Finnhub y Yahoo.',
            'No EOD backup (MarketStack/AlphaVantage): prices depend on Finnhub and Yahoo.',
            ('Opcional: crea una clave gratis en marketstack.com o alphavantage.co y ponla en Railway → tu servicio → '
             'Variables como MARKETSTACK_KEY o AV_KEY.',
             'Optional: create a free key at marketstack.com or alphavantage.co and put it in Railway → your service → '
             'Variables as MARKETSTACK_KEY or AV_KEY.'),
            configured=False, ok=False)

    # R6: salud de la investigación (cola, presupuesto, reloj) junto a los pings
    try:
        from research.health import research_health
        _rh = research_health()
        _clock = bool((_rh.get('scheduler') or {}).get('running'))
        services['investigacion'] = _diag_card(
            _rh['hint_es'] + ' · reloj del servidor: ' + ('activo' if _clock else 'APAGADO'),
            (_rh.get('hint_en') or _rh['hint_es']) + ' · server clock: ' + ('running' if _clock else 'OFF'),
            None if _rh['ok'] else _diag_research_fix(_rh),
            configured=True, ok=bool(_rh['ok']),
            health={k: _rh[k] for k in ('queue', 'budget', 'scheduler', 'outcomes', 'last_errors')})
    except Exception as _e:  # noqa: BLE001
        services['investigacion'] = _diag_card(f'sin salud de investigación: {type(_e).__name__}',
                                               f'no research health: {type(_e).__name__}',
                                               configured=True, ok=False)
    # Interfaz generativa del chat (core/genui, docs/CHAT_UI_GENERATIVA.md §11 F1): modo GENUI, ms p95 por sobre (meta
    # ≤ 25), peso p95, descartes y CIFRAS SIN PROCEDENCIA (meta 0). Solo memoria del proceso: no llama a nada.
    try:
        from core import genui as _gu
        _gs = _gu.stats()
        _p95 = _gs.get('ms_p95')
        _gok = _gu.healthy(_gs)        # ventana de 24 h + p95 con ≥ 20 muestras (no contadores de toda la vida)
        _mes = {'off': 'apagada', 'shadow': 'en sombra (se arma y se mide, no se envía)', 'on': 'encendida'}[_gs['mode']]
        _men = {'off': 'off', 'shadow': 'shadow (built and measured, not sent)', 'on': 'on'}[_gs['mode']]
        _drop = sum((_gs.get('dropped') or {}).values())
        _ms = '—' if _p95 is None else f'{_p95:.1f}'
        _kb = '—' if _gs.get('kb_p95') is None else f"{_gs['kb_p95']:.1f}"
        _pg = _gs.get('progressive') or {}
        _pges = _pgen = ''
        if _pg.get('answers'):   # F3: lo que costaron los bloques provisionales (todos los parciales de una respuesta)
            _pms = '—' if _pg.get('ms_p95') is None else f"{_pg['ms_p95']:.1f}"
            _pges = f" · progresivos: {_pg['answers']} respuestas, {_pg['builds']} armados, p95 {_pms} ms por respuesta"
            _pgen = f" · progressive: {_pg['answers']} answers, {_pg['builds']} builds, p95 {_pms} ms per answer"
        services['genui'] = _diag_card(
            f"Respuestas visuales: {_mes} · {_gs['built']} sobres ({_gs['sent']} enviados) · p95 {_ms} ms · "
            f"{_kb} KB · {_drop} bloques descartados · {_gs['unprovenanced_24h']} con cifras sin fuente (24 h)" + _pges,
            f"Visual answers: {_men} · {_gs['built']} envelopes ({_gs['sent']} sent) · p95 {_ms} ms · {_kb} KB · "
            f"{_drop} blocks dropped · {_gs['unprovenanced_24h']} with unsourced figures (24 h)" + _pgen,
            None if _gok else ('Revisa el registro del servidor (líneas «genui:»): un bloque con una cifra sin fuente '
                               'se descarta solo, pero no debería pasar.',
                               'Check the server log («genui:» lines): a block with an unsourced figure is dropped '
                               'automatically, but it should not happen.'),
            configured=True, ok=bool(_gok), genui=_gs)
    except Exception as _e:  # noqa: BLE001
        services['genui'] = _diag_card(f'sin métricas de respuestas visuales: {type(_e).__name__}',
                                       f'no visual-answer metrics: {type(_e).__name__}', configured=True, ok=True)
    # Regla bilingüe: TODA tarjeta lleva detail_en (si alguna se olvida, al menos no queda vacía en inglés)
    for _s in services.values():
        if isinstance(_s, dict) and _s.get('detail') and not _s.get('detail_en'):
            _s['detail_en'] = _s['detail']

    n_ok = sum(1 for s in services.values() if s.get('ok'))
    out = {
        'ts': int(now), 'cached': False, 'routing': _ai_route_now(),
        'jwt_api': _HAS_JWT, 'services': services,
        'summary': {'ok': n_ok, 'total': len(services)},
        'secret_key_default': _secret_key_default(),
        'security_warnings': _security_warnings(),
    }
    _DIAG_CACHE['ts'] = now
    _DIAG_CACHE['data'] = out
    return jsonify(_diag_view(out))


def _diag_view(out):
    """G5-18 (revisión lote I): el 🩺 dice papel o DINERO REAL del bróker SOLO con el PIN de operador; sin él, la
    tarjeta de Alpaca queda neutra (configurado, si responde, la pista para arreglarlo) — igual que
    /api/trade/status. Se filtra POR PEDIDO: la copia en caché guarda la versión completa."""
    al = ((out or {}).get('services') or {}).get('alpaca')
    if not isinstance(al, dict) or _operator_pin_ok('diagnostics')[0]:
        return out
    view = dict(out, services=dict(out['services']))
    a = {k: v for k, v in al.items() if k not in ('mode', 'detail', 'detail_en')}
    if not al.get('configured'):
        es, en = 'ALPACA_KEY sin configurar — el bróker está apagado.', 'ALPACA_KEY not set — the broker is off.'
    elif al.get('ok'):
        es, en = 'Bróker conectado (pon tu PIN para ver si es papel o dinero real).', \
                 'Broker connected (enter your PIN to see whether it is paper or real money).'
    else:
        es, en = 'El bróker no respondió bien (pon tu PIN para ver el detalle).', \
                 'The broker did not answer correctly (enter your PIN to see the detail).'
    if al.get('fix_es') and al.get('fix_en'):
        es, en = f"{es} — QUÉ HACER: {al['fix_es']}", f"{en} — WHAT TO DO: {al['fix_en']}"
    a.update(detail=es, detail_en=en, mode_hidden=True)
    view['services']['alpaca'] = a
    return view


# ----------------------------------------------------------------------------
# Finnhub — precios, noticias, earnings, WebSocket token
# ----------------------------------------------------------------------------
# ── WebSocket de Finnhub (auditoría #14) ─────────────────────────────────────
# El navegador necesita UNA key de Finnhub para abrir el WebSocket. Antes
# /api/ws-token + /api/ws-key se la daban a cualquiera (curl incluido). Ahora:
#   · solo peticiones del MISMO ORIGEN (Sec-Fetch-Site same-origin/none, u
#     Origin/Referer con el mismo host) — frena a otras webs que la pidan desde
#     el navegador de un visitante;
#   · el token dura 20 s, va atado a la IP (último salto de X-Forwarded-For) y
#     sirve UNA sola vez;
#   · si existe FINNHUB_WS_KEY se entrega ESA (una key aparte, solo para el
#     navegador) y la FINNHUB_KEY del servidor nunca sale. Recomendado.
# Un cliente no-navegador puede falsificar cabeceras: por eso lo correcto es
# FINNHUB_WS_KEY separada (si se filtra, se rota sin tocar el servidor).
_WS_TOKEN_TTL_S = 20
_WS_USED = {}                 # firma → vencimiento (tokens ya canjeados)
_WS_LOCK = threading.Lock()
# Clave de firma ALEATORIA por proceso (1 worker: emisión y canje ocurren en el
# mismo proceso; tokens de 20 s). No depende de SECRET_KEY → aunque siga siendo
# la de por defecto, los tokens no se pueden fabricar.
_WS_SIGN_KEY = os.urandom(32)


def _same_origin_request():
    sfs = (request.headers.get('Sec-Fetch-Site') or '').strip().lower()
    if sfs in ('same-origin', 'none'):
        return True
    if sfs in ('cross-site', 'same-site'):
        return False
    from urllib.parse import urlparse
    hosts = {h.strip().lower() for h in ((request.host or ''),
                                        (request.headers.get('X-Forwarded-Host') or '').split(',')[0]) if h.strip()}
    origin = request.headers.get('Origin')
    if origin and origin != 'null':
        return urlparse(origin).netloc.lower() in hosts
    ref = request.headers.get('Referer')
    if ref:
        return urlparse(ref).netloc.lower() in hosts
    return False


def _ws_forbidden():
    return jsonify({'error': 'Solo disponible desde la propia app (mismo origen)',
                    'error_en': 'Only available from the app itself (same origin)',
                    'code': 'cross_origin'}), 403


def _ws_sig(expires, ip):
    return hmac.new(_WS_SIGN_KEY, f'ws:{expires}:{ip}'.encode(), hashlib.sha256).hexdigest()[:24]


@app.route('/api/ws-token')
@rate_limit(limit=20, window=60)
def ws_token():
    """Token corto (20 s, atado a la IP, un solo uso) para canjear por la key
    del WebSocket en /api/ws-key. Solo desde el mismo origen."""
    if not (os.getenv('FINNHUB_WS_KEY') or FINNHUB):
        return jsonify({'error': 'falta FINNHUB_KEY en el servidor', 'error_en': 'FINNHUB_KEY is not set on the server',
                        'code': 'no_finnhub_key'}), 400
    if not _same_origin_request():
        return _ws_forbidden()
    expires = int(time.time()) + _WS_TOKEN_TTL_S
    resp = jsonify({'session_token': f'{expires}.{_ws_sig(expires, _client_ip())}',
                    'expires_in': _WS_TOKEN_TTL_S})
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@app.route('/api/ws-key', methods=['POST'])
@rate_limit(limit=20, window=60)
def ws_key():
    """Valida el session_token (fresco, misma IP, no usado) y devuelve la key
    del WebSocket: FINNHUB_WS_KEY si existe (recomendado), si no FINNHUB_KEY."""
    ws_key_value = os.getenv('FINNHUB_WS_KEY') or FINNHUB
    if not ws_key_value:
        return jsonify({'error': 'falta FINNHUB_KEY en el servidor', 'error_en': 'FINNHUB_KEY is not set on the server',
                        'code': 'no_finnhub_key'}), 400
    if not _same_origin_request():
        return _ws_forbidden()
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    token = str(data.get('session_token', ''))
    try:
        exp_s, sig = token.split('.', 1)
        expires = int(exp_s)
    except (ValueError, AttributeError):
        return jsonify({'error': 'token inválido', 'error_en': 'invalid token', 'code': 'invalid_token'}), 401
    now = time.time()
    if now > expires or expires > now + _WS_TOKEN_TTL_S + 5:
        return jsonify({'error': 'token vencido', 'error_en': 'token expired', 'code': 'token_expired'}), 401
    if not hmac.compare_digest(sig, _ws_sig(expires, _client_ip())):
        return jsonify({'error': 'firma del token inválida', 'error_en': 'invalid token signature',
                        'code': 'invalid_token'}), 401
    with _WS_LOCK:
        for k in [k for k, v in _WS_USED.items() if v < now]:
            _WS_USED.pop(k, None)
        if sig in _WS_USED:
            return jsonify({'error': 'token ya usado', 'error_en': 'token already used', 'code': 'token_used'}), 401
        _WS_USED[sig] = expires
    resp = jsonify({'token': ws_key_value})
    resp.headers['Cache-Control'] = 'no-store'
    return resp


def _quote_raw_compat(tk, row):
    """Fila del contrato /api/quotes/live + claves CRUDAS de Finnhub {c, pc, d,
    dp, t} que el cliente viejo (DataLayer.quote, X-Ray, canvas-data) sigue
    leyendo. Un solo origen de datos (core.quotes.fetch_quotes_live), dos
    vocabularios durante la transición."""
    out = dict(row)
    px, prev = row.get('live'), row.get('prev')
    out['symbol'] = tk
    out['c'] = px
    out['pc'] = prev
    out['dp'] = row.get('pct')
    try:
        out['d'] = round(float(px) - float(prev), 4) if (px is not None and prev is not None) else None
    except (TypeError, ValueError):
        out['d'] = None
    try:
        from datetime import datetime as _dt
        iso = str(row.get('as_of') or '').replace('Z', '+00:00')
        out['t'] = int(_dt.fromisoformat(iso).timestamp()) if iso else None
    except (TypeError, ValueError):
        out['t'] = None
    out['v'] = row.get('vol')
    return out


@app.route('/api/quote/<ticker>')
@rate_limit(limit=120, window=60)
@cache.cached(timeout=15, query_string=True)
def quote(ticker):
    """Cotización de UN ticker por la MISMA cascada que /api/quotes/live
    (Finnhub→Yahoo, también EE.UU.; Yahoo no necesita key). Devuelve el
    contrato {close, prev, pct, live, provider, as_of…} + {c, pc, dp, t} crudos."""
    ticker = _safe_ticker(ticker)
    if not ticker:
        return jsonify({'error': 'invalid ticker'}), 400
    from core.quotes import fetch_quotes_live
    try:
        res = fetch_quotes_live([ticker])
    except Exception as e:  # noqa: BLE001
        log.warning('quote %s: %s', ticker, type(e).__name__)
        res = {'quotes': {}, 'finnhub_quota': False}
    row = (res.get('quotes') or {}).get(ticker)
    if not row:
        return jsonify({'error': 'sin cotización disponible / no quote available', 'symbol': ticker,
                        'finnhub_quota': bool(res.get('finnhub_quota')),
                        'finnhub_configured': bool(FINNHUB)}), 503
    return jsonify(_quote_raw_compat(ticker, row))


# ── Phase 1 · M3: cotización por la capa de PROVEEDORES ─────────────────────
# Convive con /api/quote/<ticker> (que devuelve el JSON crudo de Finnhub y que
# la UI actual sigue usando): esta ruta es la que cumple el contrato de
# core/providers — esquema único, cascada con respaldo, y sobre todo `as_of` +
# `age_seconds`, que es lo que permite NO fingir tiempo real.
@app.route('/api/market/quote/<path:symbol>')
@rate_limit(limit=120, window=60)
@cache.cached(timeout=15, query_string=True)
def market_quote(symbol):
    from core.providers.market import crypto_registry, market_registry

    kind = (request.args.get('kind') or 'equity').strip().lower()
    reg = crypto_registry() if kind == 'crypto' else market_registry()
    q, intentos = reg.get_quote(symbol, prefer=request.args.get('prefer'))
    if not q:
        # Se dice POR QUÉ no hay dato, distinguiendo "sin configurar" de "falló":
        # un 404 mudo obligaría a adivinar cuál de las dos cosas pasó.
        return jsonify({'error': 'sin cotización disponible', 'symbol': symbol,
                        'attempts': intentos,
                        'providers': reg.statuses()}), 404
    return jsonify(q)


@app.route('/api/market/providers')
@rate_limit(limit=60, window=60)
def market_providers():
    """Qué proveedores hay, cuáles están configurados y por qué no los que no.
    Honestidad de fuentes (spec §13): nada de fingir integraciones activas."""
    from core.providers.market import crypto_registry, market_registry
    from core.providers.news import news_registry
    from core.quotes import finnhub_circuit_state, finnhub_quota_active
    return jsonify({
        'market': market_registry().statuses(),
        'crypto': crypto_registry().statuses(),
        'news': news_registry().statuses(),
        # circuito abierto tras HTTP 429: la UI puede decir "cuota de Finnhub
        # agotada, precios vía Yahoo" en vez de fingir que todo va bien
        'finnhub_quota': finnhub_quota_active(),
        'finnhub_circuit': finnhub_circuit_state(),
    })


@app.route('/api/scalp/price/<path:symbol>')
@rate_limit(limit=300, window=60)
@cache.cached(timeout=2, query_string=True)
def scalp_price(symbol):
    """Precio spot RÁPIDO para el scalping. Acciones → Finnhub (c/pc); cripto (par
    con '/') → datos de Alpaca (misma key). Caché 2s: fresco para scalping sin
    reventar rate limits. El cliente calcula la dirección del tick comparando lecturas."""
    sym = (symbol or '').strip().upper()
    if not sym:
        return jsonify({'error': 'symbol requerido'}), 400
    try:
        if '/' in sym:   # cripto (BTC/USD)
            if not ALPACA_KEY:
                return jsonify({'error': 'ALPACA no configurado'}), 400
            r = requests.get('https://data.alpaca.markets/v1beta3/crypto/us/latest/trades',
                             params={'symbols': sym}, headers=_alpaca_hdrs(), timeout=8)
            tr = ((r.json().get('trades') or {}).get(sym)) or {}
            p = tr.get('p')
            if p is None:
                return jsonify({'error': 'sin precio para ' + sym}), 502
            return jsonify({'symbol': sym, 'price': float(p), 'kind': 'crypto'})
        # acción (equity)
        tk = _safe_ticker(sym)
        data, err = _fetch_quote_raw(tk, timeout=5)
        if err or not data:
            return jsonify({'error': err or 'sin precio'}), 502
        return jsonify({'symbol': tk, 'price': float(data.get('c') or 0),
                        'prev': float(data.get('pc') or 0), 'kind': 'equity'})
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:150]}), 502


@app.route('/api/quotes')
@rate_limit(limit=120, window=60)
@cache.cached(timeout=15, query_string=True)
def batch_quotes():
    """Varios tickers (?symbols=A,B o ?tickers=A,B) por la MISMA cascada que
    /api/quotes/live. Mapa plano {T: fila + {c, pc, dp, t} crudos} — forma que
    canvas-data.js ya consume. Sin tickers → 400."""
    raw = request.args.get('symbols') or request.args.get('tickers') or ''
    tickers = [s for s in (_safe_ticker(t) for t in raw.split(',')) if s]
    if not tickers:
        return jsonify({'error': 'symbols required / faltan símbolos'}), 400
    from core.quotes import fetch_quotes_live
    try:
        res = fetch_quotes_live(tickers)
    except Exception as e:  # noqa: BLE001
        log.warning('quotes: %s', type(e).__name__)
        return jsonify({'error': 'error interno al consultar las fuentes / internal error'}), 503
    return jsonify({tk: _quote_raw_compat(tk, row) for tk, row in (res.get('quotes') or {}).items()})


# ── Series anuales para el DOSSIER financiero (estilo investingvisuals) ─────
# OJO: /api/fundamentals/<t> ya existe (P/E + price targets + ratings, lo usa
# el Second Brain) — este es OTRO endpoint con las series anuales de 6 años.
@app.route('/api/findossier/<ticker>')
@rate_limit(limit=240, window=3600)
def fin_dossier(ticker):
    """Series anuales para el dossier financiero de una empresa (lo consumen
    engine/fincard.js, cockpit.js, termdata.js y localcharts.js): crecimiento
    de ingresos, dilución, FCF, márgenes, deuda/capital, ROE y EV/Ventas.

    2026-09-28: la cascada vive en core/company_data.get_annual_financials —
    FMP /stable/ → Yahoo fundamentals-timeseries (TODAS las bolsas, sin clave)
    → Alpha Vantage. Antes era FMP → AV y fuera de EE.UU. casi nunca había
    datos. Mismas claves y unidades que siempre + `source` y `currency`
    (moneda ORIGINAL del reporte; los montos salen convertidos a USD).
    La caché (12 h éxito completo / 1 h parcial / 10 min fallo) está en el
    módulo: un fallo transitorio nunca queda envenenado."""
    ticker = _safe_ticker(ticker)
    if not ticker:
        return jsonify({'error': 'invalid ticker'}), 400
    from core.company_data import get_annual_financials, to_findossier
    try:
        fin = get_annual_financials(ticker, fmp_key=FMP, av_key=AV_KEY)
    except Exception as e:  # noqa: BLE001
        log.warning('findossier %s: %s', ticker, type(e).__name__)
        fin = {'available': False, 'reason': 'error interno al consultar las fuentes',
               'reason_en': 'internal error while querying the sources'}
    return jsonify(to_findossier(fin, ticker))


@app.route('/api/candles/<ticker>')
@rate_limit(limit=120, window=60)
@cache.cached(timeout=1800, query_string=True)
def candles(ticker):
    """OHLCV candles for charting, HONRANDO el timeframe (range/interval).

    Fix 2026-07-13 (Fabrizio: "día/mes/año dan el mismo gráfico"): antes esto
    ignoraba los parámetros y devolvía siempre 90 días diarios. Ahora Yahoo es
    la fuente principal y respeta ?range= (1d,5d,1mo,3mo,6mo,1y,5y,max) e
    ?interval= (5m,15m,30m,1d,1wk). Finnhub/FMP/Stooq quedan de respaldo diario.
    Devuelve la forma Finnhub {s,c,o,h,l,t} que espera el frontend.
    """
    ticker = _safe_ticker(ticker)
    if not ticker:
        return jsonify({'error': 'invalid ticker', 's': 'no_data'}), 400
    import time as _time
    # timeframe pedido (whitelist para no inyectar en la URL de Yahoo)
    _RANGES = {'1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'}
    _INTERVALS = {'5m', '15m', '30m', '60m', '1h', '1d', '1wk', '1mo'}
    rng = (request.args.get('range') or '3mo').lower()
    itv = (request.args.get('interval') or '1d').lower()
    if rng not in _RANGES:
        rng = '3mo'
    if itv not in _INTERVALS:
        itv = '1d'

    # 0) Yahoo con el timeframe pedido — PRIMARIO (respeta range+interval)
    try:
        yf0 = requests.get(
            f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}'
            f'?interval={itv}&range={rng}',
            headers={'User-Agent': 'Mozilla/5.0 (compatible; KhipuFinance/1.0)'},
            timeout=12)
        if yf0.status_code == 200:
            yd = yf0.json()
            res0 = ((yd.get('chart') or {}).get('result') or [None])[0]
            if res0:
                ts0 = res0.get('timestamp', []) or []
                qb0 = (res0.get('indicators') or {}).get('quote', [{}])[0]
                cl0 = qb0.get('close', []) or []
                if ts0 and cl0:
                    op0, hi0, lo0 = qb0.get('open', []), qb0.get('high', []), qb0.get('low', [])
                    valid0 = [(t, o, h, l, c) for t, o, h, l, c in zip(
                        ts0, op0 or [None] * len(ts0), hi0 or [None] * len(ts0),
                        lo0 or [None] * len(ts0), cl0) if c is not None]
                    if valid0:
                        return jsonify({
                            's': 'ok', 't': [v[0] for v in valid0],
                            'o': [v[1] if v[1] is not None else v[4] for v in valid0],
                            'h': [v[2] if v[2] is not None else v[4] for v in valid0],
                            'l': [v[3] if v[3] is not None else v[4] for v in valid0],
                            'c': [v[4] for v in valid0]})
    except Exception:  # noqa: BLE001
        pass

    to_ts = int(_time.time())
    from_ts = to_ts - 95 * 86400

    # 1) Finnhub (paid tier — free tier returns 403 on /stock/candle)
    if FINNHUB:
        data, err = _safe_get(
            f'https://finnhub.io/api/v1/stock/candle?symbol={ticker}'
            f'&resolution=D&from={from_ts}&to={to_ts}&token={FINNHUB}')
        if not err and data and data.get('s') == 'ok' and data.get('c'):
            return jsonify(data)

    # 2) FMP historical EOD
    if FMP:
        fmp, err = _safe_get(
            f'https://financialmodelingprep.com/api/v3/historical-price-full/'
            f'{ticker}?serietype=line&timeseries=95&apikey={FMP}')
        hist = (fmp or {}).get('historical') if isinstance(fmp, dict) else None
        if hist:
            hist = list(reversed(hist))  # FMP returns newest-first
            out = {'s': 'ok',
                   'c': [h.get('close') for h in hist],
                   'o': [h.get('open', h.get('close')) for h in hist],
                   'h': [h.get('high', h.get('close')) for h in hist],
                   'l': [h.get('low', h.get('close')) for h in hist],
                   't': [int(_time.mktime(_time.strptime(h['date'], '%Y-%m-%d')))
                         for h in hist if h.get('date')]}
            if out['c']:
                return jsonify(out)

    # 3) Yahoo Finance — unofficial but reliable from server IPs, no key needed
    try:
        yf_url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}'
                  f'?interval=1d&range=3mo')
        yf_r = requests.get(yf_url,
                             headers={'User-Agent': 'Mozilla/5.0 (compatible; Khipu/1.0)'},
                             timeout=12)
        if yf_r.status_code == 200:
            ydata = yf_r.json()
            result = ((ydata.get('chart') or {}).get('result') or [None])[0]
            if result:
                ts      = result.get('timestamp', [])
                q_block = (result.get('indicators') or {}).get('quote', [{}])[0]
                opens   = q_block.get('open', [])
                highs   = q_block.get('high', [])
                lows    = q_block.get('low', [])
                closes  = q_block.get('close', [])
                if ts and closes:
                    valid = [(t, o, h, l, c) for t, o, h, l, c
                             in zip(ts,
                                    opens  or [None]*len(ts),
                                    highs  or [None]*len(ts),
                                    lows   or [None]*len(ts),
                                    closes)
                             if c is not None]
                    if valid:
                        out = {
                            's': 'ok',
                            't': [v[0] for v in valid],
                            'o': [v[1] if v[1] is not None else v[4] for v in valid],
                            'h': [v[2] if v[2] is not None else v[4] for v in valid],
                            'l': [v[3] if v[3] is not None else v[4] for v in valid],
                            'c': [v[4] for v in valid],
                        }
                        return jsonify(out)
    except Exception:  # noqa: BLE001
        pass

    # 4) Stooq — free, no key. US tickers use the .US suffix.
    try:
        import csv as _csv
        import io as _io
        sym = ticker.lower()
        if '.' not in sym:
            sym += '.us'
        r = requests.get(f'https://stooq.com/q/d/l/?s={sym}&i=d', timeout=10)
        if r.status_code == 200 and r.text and 'Date' in r.text:
            rows = list(_csv.DictReader(_io.StringIO(r.text)))
            rows = rows[-90:]
            if rows:
                out = {'s': 'ok', 'c': [], 'o': [], 'h': [], 'l': [], 't': []}
                for row in rows:
                    try:
                        out['o'].append(float(row['Open']))
                        out['h'].append(float(row['High']))
                        out['l'].append(float(row['Low']))
                        out['c'].append(float(row['Close']))
                        out['t'].append(int(_time.mktime(
                            _time.strptime(row['Date'], '%Y-%m-%d'))))
                    except (ValueError, KeyError):
                        continue
                if out['c']:
                    return jsonify(out)
    except Exception:  # noqa: BLE001
        pass

    return jsonify({'error': 'no_data', 's': 'no_data'}), 404


# ── Alpaca paper/live trading ─────────────────────────────────────────────────
def _alpaca_hdrs():
    return {
        'APCA-API-KEY-ID': ALPACA_KEY,
        'APCA-API-SECRET-KEY': ALPACA_SECRET,
        'Content-Type': 'application/json',
    }


# PIN de trading: core.pin.require_pin (auditoría #7). Mismo contador por IP
# (ÚLTIMO salto de X-Forwarded-For) y GLOBAL que /api/brokerage y /api/mcp;
# 10 fallos/IP o 30 globales en 10 min → 429. Sin TRADE_PIN → 403
# 'trading_disabled' (seguro por defecto). Se conserva el nombre _trade_auth.
_trade_auth = _require_pin

# ── Validación de órdenes de la cuenta de la casa (auditoría #8/#9) ──────────
# tope por orden (notional o qty × precio) = el del corretaje: artefacto `policy.broker_risk` (paso 9, D2)
from core import governance as _gov  # noqa: E402
(MAX_ORDER_USD,) = _gov.bind(globals(), 'policy.broker_risk', {'MAX_ORDER_USD': 'hard_max_order_usd'})
# Base 1-10 (acciones ≤ 5 + clase; cripto hasta RENDER…) + clase opcional
# '.B' + par cripto '/USD'. Sin puntos sueltos: 'X.', '.', '..' no pasan.
_TRADE_SYM_RE = re.compile(r'^[A-Z0-9]{1,10}(\.[A-Z0-9]{1,3})?(/[A-Z]{3,5})?$')
_TRADE_TIFS = ('day', 'gtc', 'ioc', 'fok')
_CLIENT_ORDER_ID_RE = re.compile(r'^[A-Za-z0-9_\-]{8,64}$')


def _trade_symbol(raw):
    """'nvda' → 'NVDA'; 'btc/usd' → 'BTC/USD'. None si no es un símbolo válido.
    Bloquea '.', '..', '?cancel_orders=true', rutas y cualquier cosa que al
    ir en la URL de Alpaca pudiera apuntar a otro endpoint (p. ej. cerrar TODO)."""
    sym = str(raw or '').strip()
    if not sym or not sym.isascii():        # 'ß'.upper() == 'SS': se valida ANTES de .upper()
        return None
    sym = sym.upper()
    return sym if _TRADE_SYM_RE.match(sym) else None


_PAPER_HOSTS = ('paper-api.alpaca.markets',)


def _paper():
    """¿Cuenta de PAPEL? Por el HOST de ALPACA_BASE (no por la subcadena 'paper':
    un proxy de la cuenta real con 'paper' en el nombre habilitaba el modo AUTO
    con dinero real). Host desconocido → se trata como DINERO REAL (seguro)."""
    from urllib.parse import urlparse
    try:
        host = (urlparse(str(ALPACA_BASE or '').strip()).hostname or '').lower()
    except Exception:  # noqa: BLE001
        return False
    return host in _PAPER_HOSTS


def _account_is_live(account):
    """El número de cuenta de papel de Alpaca empieza por 'PA'. Si la cuenta
    trae account_number y NO empieza por 'PA' → dinero real, diga lo que diga
    la URL. Sin el dato → None (se decide por el host)."""
    num = str((account or {}).get('account_number') or '').strip().upper() if isinstance(account, dict) else ''
    return (not num.startswith('PA')) if num else None


def _house_trading_enabled():
    """Interruptor general BROKERAGE_TRADING_ENABLED (=off → ninguna orden:
    /api/trade/order, /api/trade/close y el agente de trading)."""
    try:
        from brokerage.risk import trading_enabled
        return bool(trading_enabled())
    except Exception:  # noqa: BLE001 — sin el paquete brokerage, se lee el env igual
        return (os.getenv('BROKERAGE_TRADING_ENABLED', 'on') or 'on').strip().lower() in \
            ('on', '1', 'true', 'yes', 'si', 'sí')


def _house_ledger_block():
    """INFRA_OPERATIVA paso 7: con la cadena del libro de decisiones ROTA (sin reconocer con PIN) la cuenta de la
    casa en DINERO REAL no envía órdenes (tampoco cierres); el papel sigue. None = puede seguir."""
    if _paper():
        return None
    try:
        from core.ledger import money_gate
        ok, es, en = money_gate()
    except Exception:  # noqa: BLE001 — falla cerrado
        ok, es, en = False, 'No se pudo comprobar la cadena del libro de decisiones', 'Could not check the ledger chain'
    if ok:
        return None
    return jsonify({'error': es, 'error_en': en, 'code': 'ledger_chain_broken'}), 423


def _trading_halted_response():
    return jsonify({'error': 'Interruptor general APAGADO (BROKERAGE_TRADING_ENABLED=off): no se envía ninguna orden',
                    'error_en': 'Master switch OFF (BROKERAGE_TRADING_ENABLED=off): no orders are sent',
                    'code': 'trading_halted'}), 423


def _broker_missing_response():
    return jsonify({'error': 'Bróker no configurado: faltan ALPACA_KEY/ALPACA_SECRET en Railway',
                    'error_en': 'Broker not configured: ALPACA_KEY/ALPACA_SECRET missing in Railway',
                    'code': 'broker_not_configured'}), 400


def _trade_actor():
    """Paso 5 (INFRA_OPERATIVA §8.1): quien opera la cuenta de la casa es el PRINCIPAL autenticado (el PIN →
    op:fabrizio; el hilo del agente → system:trading_agent), no el texto de X-Khipu-Actor, que queda como
    etiqueta en broker_audit.detail._who."""
    try:
        from core import identity
        return identity.principal_from_request().id
    except Exception:  # noqa: BLE001 — fuera de una petición y sin principal atado
        return 'system:unknown'


def _trade_audit(action, detail, actor=None):
    """Rastro APPEND-ONLY de cada intento de orden de la cuenta de la casa
    (auditoría #21): broker_audit vía brokerage.service.audit si hay base; si
    no, al log. Nunca guarda secretos ni rompe la operación."""
    detail = dict(detail or {})
    detail.setdefault('paper', _paper())
    try:
        detail.setdefault('ip', _client_ip())
    except Exception:  # noqa: BLE001 — hilo del agente: sin petición
        pass
    actor = actor or _trade_actor()
    log.info('TRADE-AUDIT %s %s %s', actor, action, json.dumps(detail, default=str)[:600])
    try:
        from ontology.db import ontology_available
        if not ontology_available():
            return
        from ontology.db import session_scope
        from brokerage.service import audit
        with session_scope() as s:
            audit(s, actor, action, detail=detail)
    except Exception as e:  # noqa: BLE001
        log.warning('trade-audit: no se registró %s en broker_audit (%s)', action, type(e).__name__)


def _alpaca_json(r):
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return None


def _finite_pos(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if (f == f and f not in (float('inf'), float('-inf')) and f > 0) else None


def _num_str(v):
    """12.0 → '12'; 0.5 → '0.5'; hasta 9 decimales (fracciones de Alpaca), sin notación científica."""
    return ('%.9f' % float(v)).rstrip('0').rstrip('.')


def _bad(es, en, code='bad_request', status=400, **extra):
    return jsonify({'error': es, 'error_en': en, 'code': code, **extra}), status


def _bad_json_body():
    """Cuerpo JSON que no es un objeto ([1,2], "NVDA"…): 400 bilingüe (antes 500)."""
    return _bad('Cuerpo JSON inválido: se esperaba un objeto {…}', 'Invalid JSON body: an object {…} was expected',
                code='bad_json')


def _json_object_body():
    """→ (dict, None) o (None, respuesta_400). Cuerpo ausente/ilegible = {}."""
    data = request.get_json(silent=True)
    if data is None:
        return {}, None
    if not isinstance(data, dict):
        return None, _bad_json_body()
    return data, None


@app.route('/api/trade/account', methods=['GET'])
@rate_limit(limit=60, window=60)
@_trade_auth
def trade_account():
    if not ALPACA_KEY:
        return _broker_missing_response()
    try:
        r = requests.get(f'{ALPACA_BASE}/v2/account',
                         headers=_alpaca_hdrs(), timeout=10)
        try:
            payload = r.json()
            # "paper": true → cuenta simulada (paper-api); false → DINERO REAL.
            # La UI usa este flag para el badge 🧪 SIMULADO / 🔴 DINERO REAL.
            if isinstance(payload, dict):
                payload['paper'] = _paper() and _account_is_live(payload) is not True
            return jsonify(payload), r.status_code
        except Exception:
            return jsonify({'error': f'Alpaca HTTP {r.status_code}', 'body': r.text[:300]}), 502
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200], 'base': ALPACA_BASE, 'key_set': bool(ALPACA_KEY)}), 502


_TRADE_STATUS_CACHE = {'ts': 0.0, 'data': None}
_TRADE_STATUS_TTL_S = 30


@app.route('/api/trade/status', methods=['GET'])
@rate_limit(limit=30, window=60)
def trade_status():
    """Diagnóstico PÚBLICO no sensible del bróker (sin PIN): NO expone claves ni
    datos de cuenta — solo si están configuradas, la base y el status HTTP del
    endpoint de cuenta, con una pista accionable. Para depurar el 'Alpaca HTTP
    404' desde cualquier dispositivo sin conocer el TRADE_PIN. Caché 30 s en
    memoria (auditoría #7: antes cada visita anónima llamaba a Alpaca)."""
    now = time.time()
    cached = _TRADE_STATUS_CACHE['data']
    if cached is not None and now - _TRADE_STATUS_CACHE['ts'] < _TRADE_STATUS_TTL_S:
        return jsonify(_trade_status_view(dict(cached, cached=True)))
    info = {'key_set': bool(ALPACA_KEY), 'secret_set': bool(ALPACA_SECRET),
            'base': ALPACA_BASE, 'pin_set': bool(os.getenv('TRADE_PIN', '')), 'paper': _paper(),
            'trading_enabled': _house_trading_enabled()}
    if not ALPACA_KEY or not ALPACA_SECRET:
        info['ok'] = False
        info['hint'] = 'Faltan ALPACA_KEY/ALPACA_SECRET en Railway.'
        info['hint_en'] = 'ALPACA_KEY/ALPACA_SECRET missing in Railway.'
    else:
        try:
            r = requests.get(f'{ALPACA_BASE}/v2/account', headers=_alpaca_hdrs(), timeout=10)
            info['account_status'] = r.status_code
            info['ok'] = (r.status_code == 200)
            if r.status_code == 200:
                info['hint'], info['hint_en'] = 'Bróker OK.', 'Broker OK.'
            elif r.status_code in (401, 403):
                info['hint'] = 'Claves rechazadas: revisa ALPACA_KEY/SECRET y que coincidan con la base (paper vs live).'
                info['hint_en'] = 'Keys rejected: check ALPACA_KEY/SECRET and that they match the base (paper vs live).'
            elif r.status_code == 404:
                info['hint'] = ('URL no encontrada: ALPACA_BASE debe ser https://paper-api.alpaca.markets '
                                '(sin /v2 ni barra final).')
                info['hint_en'] = 'URL not found: ALPACA_BASE must be https://paper-api.alpaca.markets (no /v2).'
            else:
                info['hint'] = f'Alpaca respondió HTTP {r.status_code}.'
                info['hint_en'] = f'Alpaca answered HTTP {r.status_code}.'
        except Exception as e:  # noqa: BLE001
            info['ok'] = False
            info['error'] = _diag_redact(e)
            info['error_type'] = type(e).__name__     # lo único del error que se ve SIN PIN (el texto delata el host)
            info['hint'] = 'No se pudo conectar con Alpaca — revisa ALPACA_BASE.'
            info['hint_en'] = 'Could not reach Alpaca — check ALPACA_BASE.'
    _TRADE_STATUS_CACHE.update(ts=now, data=info)
    return jsonify(_trade_status_view(dict(info)))


# G5-18 (lote I1): papel o DINERO REAL (y la URL del bróker, que lo delata: paper-api vs api) SOLO con el PIN. Sin él
# la respuesta es neutra: si hay claves, si el bróker contesta y la pista para arreglarlo. `pin_set` sigue siendo
# público: el navegador lo necesita para no mandar órdenes sin PIN (y no dice nada de la cuenta).
_TRADE_STATUS_PRIVATE = ('paper', 'base')


def _operator_pin_ok(where):
    """(ok, bloqueado): PIN válido en X-Trade-Pin; `bloqueado` = el candado de PIN está activo (429). Revisión
    lote I: un candado NO es un PIN incorrecto — el cliente solo borra el PIN guardado ante invalid_pin."""
    got = request.headers.get('X-Trade-Pin', '')
    if not (got and os.getenv('TRADE_PIN', '')):
        return False, False
    from core import pin as _pin_mod
    bad = _pin_mod.check(got, where=where)
    if bad is None:
        return True, False
    return False, bool(isinstance(bad, tuple) and len(bad) > 1 and bad[1] == 429)


def _trade_status_view(info):
    got = request.headers.get('X-Trade-Pin', '')
    if got and os.getenv('TRADE_PIN', ''):
        ok, locked = _operator_pin_ok('trade_status')
        if ok:
            info['pin_valid'] = True
            return info
        if locked:
            info['pin_locked'] = True        # ni válido ni inválido: el candado no compara el PIN
        else:
            info['pin_valid'] = False
    for k in _TRADE_STATUS_PRIVATE:
        info.pop(k, None)
    if info.get('error'):                    # revisión lote I: el texto de la excepción trae el host (paper-api vs api)
        info['error'] = info.pop('error_type', None) or 'error'
    info.pop('error_type', None)
    info['mode_hidden'] = True
    return info


@app.route('/api/trade/diag', methods=['GET'])
@rate_limit(limit=10, window=60)
@_trade_auth
def trade_diag():
    """Diagnóstico del broker Alpaca — SIN exponer claves. Prueba cada llamada
    (cuenta, posiciones, órdenes, activos cripto, reloj) y devuelve status +
    primeros caracteres del error de cada una. Para depurar en producción el
    "http 404 / could not fetch equity" sin ver la pantalla del usuario."""
    def _mask(s):
        s = s or ''
        if len(s) <= 6:
            return 'set' if s else 'unset'
        return s[:4] + '…' + s[-2:]

    if not ALPACA_KEY:
        return jsonify({'ok': False, 'base': ALPACA_BASE,
                        'error': 'ALPACA_KEY sin configurar · ALPACA_KEY not configured',
                        'key': _mask(ALPACA_KEY), 'secret_set': bool(ALPACA_SECRET)}), 400

    probes = [
        ('account',       '/v2/account',   None),
        ('positions',     '/v2/positions', None),
        ('orders',        '/v2/orders',    {'status': 'all', 'limit': 1}),
        ('crypto_assets', '/v2/assets',    {'asset_class': 'crypto', 'status': 'active'}),
        ('clock',         '/v2/clock',     None),
    ]
    checks = []
    for name, path, params in probes:
        entry = {'name': name, 'path': path}
        try:
            r = requests.get(f'{ALPACA_BASE}{path}', headers=_alpaca_hdrs(),
                             params=params, timeout=10)
            entry['status'] = r.status_code
            entry['ok'] = (r.status_code == 200)
            if r.status_code != 200:
                entry['error'] = (r.text or '')[:160]
            elif name == 'account':
                # pista útil: ¿trae equity? (sin exponer montos exactos)
                try:
                    entry['has_equity'] = bool(float((r.json() or {}).get('equity', 0) or 0) > 0)
                except Exception:  # noqa: BLE001
                    entry['has_equity'] = False
        except Exception as e:  # noqa: BLE001
            entry['ok'] = False
            entry['status'] = None
            entry['error'] = str(e)[:160]
        checks.append(entry)

    account_ok = next((c['ok'] for c in checks if c['name'] == 'account'), False)
    return jsonify({
        'ok': bool(account_ok),
        'base': ALPACA_BASE,
        'paper': _paper(),
        'key': _mask(ALPACA_KEY),
        'secret_set': bool(ALPACA_SECRET),
        'checks': checks,
        'hint': None if account_ok else (
            'Si account da 404: revisa ALPACA_BASE (paper=https://paper-api.alpaca.markets, '
            'live=https://api.alpaca.markets, sin barra final). Si da 401/403: revisa '
            'ALPACA_KEY/ALPACA_SECRET (¿de paper o de live?). · If account 404s check '
            'ALPACA_BASE; if 401/403 check the keys (paper vs live).'),
    })

# ── Catálogo cripto de Alpaca (cache 1h en variable de módulo) ───────────────
# OJO: @cache.cached NO sirve aquí — al envolver una ruta con @_trade_auth
# cachearía también los 403/401 del guard. Patrón _13f_cache: payload +
# timestamp en una variable de módulo (1 worker → sin divergencia de estado).
_crypto_assets_cache: dict = {}


def _fetch_crypto_assets():
    """[{symbol,name}] de los pares cripto tradeables en Alpaca (p.ej.
    'BTC/USD'). Devuelve None si el catálogo no se pudo cargar — el caller
    decide el fallback (validación permisiva en trade_order)."""
    if _crypto_assets_cache and time.time() - _crypto_assets_cache.get('ts', 0) < 3600:
        return _crypto_assets_cache.get('assets')
    try:
        r = requests.get(f'{ALPACA_BASE}/v2/assets',
                         params={'asset_class': 'crypto', 'status': 'active'},
                         headers=_alpaca_hdrs(), timeout=12)
        if r.status_code != 200:
            return None
        raw = r.json()
        if not isinstance(raw, list):
            return None
        assets = [{'symbol': a.get('symbol', ''), 'name': a.get('name') or a.get('symbol', '')}
                  for a in raw if a.get('symbol') and a.get('tradable', True)]
        if not assets:
            return None
        _crypto_assets_cache['assets'] = assets
        _crypto_assets_cache['ts'] = time.time()
        return assets
    except Exception:  # noqa: BLE001
        return None


@app.route('/api/trade/crypto/assets', methods=['GET'])
@rate_limit(limit=30, window=60)
@_trade_auth
def trade_crypto_assets():
    """Activos cripto tradeables en Alpaca → {"assets":[{symbol,name}], "paper":bool}."""
    if not ALPACA_KEY:
        return _broker_missing_response()
    assets = _fetch_crypto_assets()
    if assets is None:
        return jsonify({'error': 'No se pudo cargar el catálogo cripto de Alpaca'}), 502
    return jsonify({'assets': assets, 'paper': _paper()})


# ── UN SOLO CAMINO DE DINERO (INFRA_OPERATIVA pasos 15-16; BRECHAS G5-01, M-code-03) ─────────────────────────
# /api/trade/order y /api/trade/close (panel, cripto, voz, terminal, Cabina) y el agente de trading ya NO hablan
# con Alpaca: validan la forma del pedido y llaman a brokerage.service.house_order / house_close = preview_order
# (cuenta «house») + confirm_order con los MISMOS controles (run_checks; límites de HOY mientras BRECHAS #1 siga
# abierta), client_order_id, broker_audit, candado del libro (money_gate) y decisiones order.* en el libro. La
# respuesta conserva el contrato de siempre (id, status, paper, duplicate) para no romper la UI.
_HOUSE_BLOCK_HTTP = (       # control que bloqueó → (HTTP, code); el primero de la lista que haya fallado manda
    ('kill_switch', 423, 'trading_halted'), ('ledger_chain', 423, 'ledger_chain_broken'),
    ('mode', 403, 'live_not_enabled'), ('client_status', 423, 'client_paused'),
    ('account', 502, 'account_unavailable'), ('symbol', 400, 'not_tradable'), ('restricted', 403, 'restricted'),
    ('order_size', 400, 'over_cap'), ('unresolved', 409, 'unresolved_order'),
)
_HOUSE_ERR_HTTP = {'bad_request': 400, 'over_cap': 400, 'not_found': 404, 'no_position': 404,
                   'trading_halted': 423, 'unknown_state': 502, 'broker_error': 502, 'ledger_unavailable': 503,
                   'paper_only_without_db': 403, 'broker_not_configured': 400, 'requires_human_approval': 202,
                   'expired': 409, 'used': 409, 'account_changed': 409, 'source_mismatch': 403,
                   'memo_not_approved': 409}


def _house_http(res):
    """Resultado de brokerage.service.house_order/house_close → (cuerpo, HTTP) con el contrato de /api/trade/order:
    éxito = la orden de Alpaca (id, status…) + paper + duplicate; error = {error, error_en, code} bilingüe."""
    res = res or {}
    order = res.get('order') if isinstance(res.get('order'), dict) else (res if res.get('preview_id') else {})
    paper = (order.get('mode') or ('paper' if _paper() else 'live')) != 'live'
    warn = [c.get('detail_en') or c.get('detail') for c in (order.get('checks') or [])
            if c.get('warn') and c.get('shadow')]
    common = {'paper': paper, 'decision_id': res.get('decision_id'), 'preview_id': order.get('id')}
    if res.get('ok') and not res.get('blocked') and not res.get('requires_human_approval'):
        body = dict(res.get('alpaca') or {})
        body.setdefault('id', order.get('alpaca_order_id'))
        body.setdefault('status', order.get('alpaca_status') or order.get('status'))
        body.setdefault('client_order_id', order.get('client_order_id'))
        body.update(common, order=order)
        if warn:
            body['warnings'] = warn
        if res.get('duplicate'):
            body['duplicate'] = True
        return body, 200
    if res.get('requires_human_approval') and not res.get('blocked'):
        return dict(common, status='pending_approval', order=order, duplicate=bool(res.get('duplicate')),
                    error='La orden espera tu aprobación con PIN en 👥 Clientes → Aprobaciones',
                    error_en='The order awaits your approval with the PIN in 👥 Clients → Approvals',
                    code='pending_approval'), 202
    failed = set(res.get('failed_checks') or [c.get('name') for c in (order.get('checks') or [])
                                               if not c.get('ok') and c.get('severity', 'block') == 'block'])
    code, http = res.get('code') or 'error', None
    if failed or res.get('blocked') or code == 'blocked':
        http, code = 422, 'risk_blocked'
        for name, st, c in _HOUSE_BLOCK_HTTP:
            if name in failed:
                http, code = st, c
                if name == 'order_size' and order.get('est_usd') is None:
                    http, code = 422, 'price_unavailable'
                break
    elif code == 'broker_rejected':
        http = res.get('http_status') if isinstance(res.get('http_status'), int) and \
            400 <= res.get('http_status') < 600 else 422
    elif code == 'unknown_state':
        http, code = 502, 'broker_unreachable'
    if http is None:
        http = _HOUSE_ERR_HTTP.get(code, 400)
    body = dict(common, error=res.get('error') or 'Orden no enviada', error_en=res.get('error_en') or
                res.get('error') or 'Order not sent', code=code, order=order or None,
                failed_checks=sorted(failed) or None)
    if code == 'broker_unreachable':
        body['client_order_id'] = order.get('client_order_id')
    return body, http


def _house_call(fn, *args, **kw):
    """brokerage.service.<fn>(session, …) con la base (sesión propia, se confirma al volver) o sin ella (D4: solo
    desarrollo y papel). El libro caído → 503 ledger_unavailable: sin decisión no hay orden."""
    from brokerage import service as _bsvc
    from ontology.db import ontology_available
    _bsvc.send_trace_begin()
    try:
        if ontology_available():
            from ontology.db import session_scope
            with session_scope() as s:
                return getattr(_bsvc, fn)(s, *args, **kw)
        return getattr(_bsvc, fn)(None, *args, **kw)
    except Exception as e:  # noqa: BLE001
        sent = _bsvc.send_trace()
        if not sent:
            return _house_call_error(fn, e)
        # revisión batch E: la orden YA salió hacia Alpaca y lo que falló fue guardar el resultado (commit caído,
        # timeout): NUNCA «no se envió nada» — estado DESCONOCIDO (502), con su client_order_id para que el
        # navegador lo conserve y un reintento idéntico ADOPTE la orden en vez de crear otra.
        _bsvc.record_unknown_after_send(sent, kw.get('requested_by') or 'ui', type(e).__name__,
                                        source=kw.get('source') or 'ui')
        return {'ok': False, 'code': 'unknown_state', 'order': {'client_order_id': sent[-1]},
                'error': (f'La orden se envió a Alpaca pero no se pudo guardar su resultado ({type(e).__name__}): '
                          'su estado es DESCONOCIDO. Revisa tus órdenes antes de repetirla; repetirla con el mismo '
                          'identificador no la duplica'),
                'error_en': (f'The order was sent to Alpaca but its result could not be saved ({type(e).__name__}): '
                             'its state is UNKNOWN. Check your orders before repeating it; repeating it with the '
                             'same identifier does not duplicate it')}


def _house_call_error(fn, e):
    """Error de _house_call ANTES de tocar Alpaca: no salió nada (D4: falla cerrado)."""
    from core.decisions import LedgerUnavailable
    if isinstance(e, LedgerUnavailable):
        log.error('trade: libro de decisiones no disponible (%s)', e)
        return {'ok': False, 'code': 'ledger_unavailable',
                'error': 'El libro de decisiones no está disponible: no se envió ninguna orden',
                'error_en': 'The decision ledger is unavailable: no order was sent'}
    log.error('trade: %s falló (%s)', fn, type(e).__name__)      # base caída (D4: falla cerrado) u otro error
    return {'ok': False, 'code': 'ledger_unavailable' if 'OperationalError' in type(e).__name__ else 'error',
            'error': f'No se pudo procesar la orden ({type(e).__name__}): no se envió nada',
            'error_en': f'The order could not be processed ({type(e).__name__}): nothing was sent'}


def _trade_channel_proof(data, channel):
    """Voz (paso 16): el sha del resumen que se LEYÓ en voz alta antes del «sí» + cuándo se confirmó."""
    if channel != 'voice':
        return None
    sha = str(data.get('readback_sha') or '').strip().lower()
    proof = {'kind': 'voice_readback', 'window_s': 180}
    if re.fullmatch(r'[0-9a-f]{64}', sha):
        proof['readback_sha'] = sha
    ca = str(data.get('confirmed_at') or '').strip()[:40]
    if ca:
        proof['confirmed_at'] = ca
    return proof


@app.route('/api/trade/close', methods=['POST'])
@rate_limit(limit=30, window=60)
@_trade_auth
def trade_close():
    """Cierra por completo UNA posición (1-clic 'CLOSE' del scalping) por el camino único: una orden de mercado por
    TODA la cantidad (brokerage.service.house_close: mismos controles, client_order_id, auditoría y decisiones).
    Antes era DELETE /v2/positions sin controles (M-code-03). El símbolo se valida estricto (auditoría #8)."""
    if not ALPACA_KEY:
        return _broker_missing_response()
    body = request.get_json(force=True, silent=True)
    if body is None:
        body = {}
    if not isinstance(body, dict):
        return _bad_json_body()
    raw = str(body.get('symbol') or '').strip()
    if not raw:
        return _bad('symbol requerido', 'symbol is required')
    symbol = _trade_symbol(raw)
    if not symbol:
        _trade_audit('trade_close', {'symbol': raw[:24], 'outcome': 'rejected_invalid_symbol'})
        return _bad('Símbolo inválido', 'Invalid symbol', code='invalid_symbol')
    if not _house_trading_enabled():
        _trade_audit('trade_close', {'symbol': symbol, 'outcome': 'blocked_kill_switch'})
        return _trading_halted_response()
    _lb = _house_ledger_block()
    if _lb is not None:
        _trade_audit('trade_close', {'symbol': symbol, 'outcome': 'blocked_ledger_chain'})
        return _lb
    coid = str(body.get('client_order_id') or '').strip()
    if coid and not _CLIENT_ORDER_ID_RE.match(coid):
        return _bad('client_order_id inválido (8-64 caracteres: letras, números, - o _)',
                    'Invalid client_order_id (8-64 chars: letters, digits, - or _)')
    coid = coid or ('kh-close-' + uuid.uuid4().hex[:24])
    channel = _identity_channel()
    res = _house_call('house_close', symbol, client_order_id=coid, channel=channel, requested_by=_trade_actor())
    payload, st = _house_http(res)
    _trade_audit('trade_close', {'symbol': symbol, 'outcome': 'submitted' if st == 200 else (
                                     'unknown_error' if st == 502 and payload.get('code') == 'broker_unreachable'
                                     else 'rejected'),
                                 'http_status': st, 'code': payload.get('code'), 'client_order_id': coid,
                                 'alpaca_order_id': payload.get('id') if st == 200 else None,
                                 'preview_id': payload.get('preview_id'), 'decision_id': payload.get('decision_id')})
    return jsonify(payload), st


def _identity_channel():
    try:
        from core import identity
        return identity.channel_from_request('ui')
    except Exception:  # noqa: BLE001
        return 'ui'


@app.route('/api/trade/order', methods=['POST'])
@rate_limit(20, 60)
@_trade_auth
def trade_order():
    """Orden de la cuenta de la casa por el camino ÚNICO (brokerage.service.house_order). Aquí solo se valida la
    FORMA del pedido (auditoría #9/#21): símbolo estricto, side, type market|limit, limit_price > 0, time_in_force,
    exactamente uno de qty | notional, client_order_id (8-64), cripto del catálogo de Alpaca (cripto → gtc). Los
    montos, el tope de US$100.000, el dinero real, el interruptor y el candado del libro los decide run_checks.
    · client_order_id (el del cliente o uno del servidor) es el de la orden en Alpaca: un reintento o el doble clic
      voz+botón NO duplica (200 + duplicate:true con la orden que ya existía);
    · voz: X-Khipu-Channel: voice + readback_sha (sha del resumen leído en voz alta) + confirmed_at;
    · cada intento queda en broker_audit (trade_order) y, con base, en el libro de decisiones."""
    if not ALPACA_KEY:
        return _broker_missing_response()
    data = request.get_json(silent=True)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return _bad_json_body()
    raw_sym = str(data.get('symbol') or '').strip()
    ticker = _trade_symbol(raw_sym)
    qty = data.get('qty')
    notional = data.get('notional')
    side = str(data.get('side') or 'buy').lower().strip()
    otype = str(data.get('type') or 'market').lower().strip()
    tif = str(data.get('time_in_force') or 'day').lower().strip()
    coid = data.get('client_order_id')

    def _short(v):
        return str(v)[:32] if isinstance(v, (int, float, str)) and not isinstance(v, bool) else None
    summary = {'symbol': ticker or raw_sym[:24], 'side': side[:8], 'type': otype[:16], 'tif': tif[:8],
               'qty': _short(qty), 'notional': _short(notional), 'limit_price': _short(data.get('limit_price')),
               'client_order_id': str(coid)[:64] if coid else None}

    def reject(es, en, code='bad_request', status=400):
        _trade_audit('trade_order', dict(summary, outcome='rejected', reason=code))
        return _bad(es, en, code=code, status=status)

    if not ticker:
        return reject('Símbolo inválido', 'Invalid symbol', 'invalid_symbol')
    if side not in ('buy', 'sell'):
        return reject('side debe ser buy o sell', "side must be 'buy' or 'sell'")
    if otype not in ('market', 'limit'):
        return reject("Tipo de orden no soportado: usa 'market' o 'limit'",
                      "Unsupported order type: use 'market' or 'limit'", 'unsupported_type')
    if tif not in _TRADE_TIFS:
        return reject('time_in_force debe ser day, gtc, ioc o fok', 'time_in_force must be day, gtc, ioc or fok')
    limit_price = None
    if otype == 'limit':
        limit_price = _finite_pos(data.get('limit_price'))
        if limit_price is None:
            return reject('Una orden limit requiere limit_price numérico mayor que 0',
                          'A limit order needs a numeric limit_price greater than 0')
    if coid is not None and coid != '':
        coid = str(coid).strip()
        if not _CLIENT_ORDER_ID_RE.match(coid):
            return reject('client_order_id inválido (8-64 caracteres: letras, números, - o _)',
                          'Invalid client_order_id (8-64 chars: letters, digits, - or _)')
    else:
        coid = 'kh-' + uuid.uuid4().hex
    summary['client_order_id'] = coid
    # Exactamente UNO de qty | notional (notional = monto en USD, ej. 100 = $100)
    if (qty is None) == (notional is None):
        return reject('Envía exactamente uno de: qty O notional (monto en USD)',
                      'Send exactly one of: qty OR notional (USD amount)')
    if '/' in ticker:
        # Cripto ('BTC/USD'): validar contra el catálogo de Alpaca; si el
        # catálogo no carga, fallback PERMISIVO (que Alpaca decida el 4xx).
        catalog = _fetch_crypto_assets()
        if catalog is not None and ticker not in {a['symbol'] for a in catalog}:
            return reject(f'{ticker} no es un par cripto tradeable en Alpaca',
                          f'{ticker} is not a tradable crypto pair on Alpaca', 'not_tradable')
        tif = 'gtc'   # Alpaca solo acepta gtc/ioc en cripto — se fuerza gtc
        summary['tif'] = tif
    if notional is not None:
        notional = _finite_pos(notional)
        if notional is None:
            return reject('notional debe ser un número mayor que 0 (monto en USD)',
                          'notional must be a number greater than 0 (USD amount)')
        if not (1 <= notional <= MAX_ORDER_USD):
            return reject(f'notional fuera de rango: mínimo $1, máximo ${MAX_ORDER_USD:,.0f} por orden',
                          f'notional out of range: minimum $1, maximum ${MAX_ORDER_USD:,.0f} per order', 'over_cap')
        notional = round(notional, 2)
    else:
        q = _finite_pos(qty)
        if q is None or _num_str(q) in ('', '0'):      # 1e-10 → '0' en Alpaca: se rechaza aquí
            return reject('qty debe ser un número mayor que 0 (hasta 9 decimales)',
                          'qty must be a number greater than 0 (up to 9 decimals)')
        if q > 1e7:
            return reject('qty demasiado grande', 'qty too large', 'over_cap')
        qty = float(_num_str(q))
    if not _house_trading_enabled():
        _trade_audit('trade_order', dict(summary, outcome='blocked_kill_switch'))
        return _trading_halted_response()
    _lb = _house_ledger_block()
    if _lb is not None:
        _trade_audit('trade_order', dict(summary, outcome='blocked_ledger_chain'))
        return _lb
    channel = _identity_channel()
    res = _house_call('house_order', ticker, side, notional=notional if notional is not None else None,
                      qty=qty if notional is None else None, order_type=otype, limit_price=limit_price,
                      time_in_force=tif, client_order_id=coid, source='ui', channel=channel,
                      requested_by=_trade_actor(), channel_proof=_trade_channel_proof(data, channel))
    payload, st = _house_http(res)
    o = payload.get('order') or {}
    outcome = {200: 'duplicate' if payload.get('duplicate') else 'submitted', 202: 'pending_approval'}.get(
        st, 'unknown_error' if st == 502 and payload.get('code') == 'broker_unreachable' else 'rejected')
    _trade_audit('trade_order', dict(
        summary, outcome=outcome, http_status=st, reason=payload.get('code') if st >= 400 else None,
        est_usd=o.get('est_usd'), alpaca_order_id=payload.get('id') if st == 200 else None,
        alpaca_status=payload.get('status') if st == 200 else None, preview_id=payload.get('preview_id'),
        decision_id=payload.get('decision_id'), channel=channel,
        alpaca_message=(str(payload.get('error'))[:160] if st >= 400 else None)))
    return jsonify(payload), st


@app.route('/api/news/<ticker>')
@rate_limit(limit=120, window=60)
@cache.cached(timeout=1800)  # 30 min
def company_news(ticker):
    if not FINNHUB:
        return jsonify([])
    ticker = _safe_ticker(ticker)
    if not ticker:
        return jsonify([])
    today = date.today().isoformat()
    month_ago = (date.today() - timedelta(days=30)).isoformat()
    data, err = _safe_get(
        f'https://finnhub.io/api/v1/company-news?symbol={ticker}'
        f'&from={month_ago}&to={today}&token={FINNHUB}')
    if err or not isinstance(data, list):
        return _degraded(jsonify([]))
    return jsonify(data[:20])


# ── Cripto (core/providers/coingecko.py — adapter, esquema CryptoAsset) ──────

@app.route('/api/crypto/markets')
@rate_limit(limit=60, window=60)
@cache.cached(timeout=120, query_string=True)
def crypto_markets():
    from core.providers import coingecko
    per_page = request.args.get('per_page', 100)
    page = request.args.get('page', 1)
    try:
        data, err = coingecko.list_markets(per_page=per_page, page=page)
    except Exception as e:  # noqa: BLE001
        data, err = None, str(e)[:120]
    if err:
        return jsonify({'error': err}), 502
    return jsonify({'assets': data, 'source': 'coingecko'})


@app.route('/api/crypto/<coin_id>')
@rate_limit(limit=60, window=60)
@cache.cached(timeout=300)
def crypto_detail(coin_id):
    from core.providers import coingecko
    try:
        data, err = coingecko.get_asset(coin_id)
    except Exception as e:  # noqa: BLE001
        data, err = None, str(e)[:120]
    if err:
        return jsonify({'error': err}), 502 if err != 'id inválido' else 400
    return jsonify(data)


@app.route('/api/crypto/<coin_id>/history')
@rate_limit(limit=60, window=60)
@cache.cached(timeout=600, query_string=True)
def crypto_history(coin_id):
    from core.providers import coingecko
    days = request.args.get('days', 90)
    try:
        data, err = coingecko.get_history(coin_id, days=days)
    except Exception as e:  # noqa: BLE001
        data, err = None, str(e)[:120]
    if err:
        return jsonify({'error': err}), 502 if err != 'id inválido' else 400
    return jsonify(data)


# ── Cripto IA — análisis CAUTO bilingüe (Sonnet 5, tier deep) ───────────────
def _no_ai_error(lang='es'):
    """Sin ninguna clave de IA: el mensaje en el idioma de quien pregunta (+ los dos, como en el comité)."""
    es = 'Ningún proveedor de IA configurado. Revisa 🩺 Sistema.'
    en = 'No AI provider configured. Check 🩺 System.'
    return {'ok': False, 'error': en if lang == 'en' else es, 'error_es': es, 'error_en': en, 'code': 'no_ai'}


def _ai_friendly_error(e):
    """Texto para personas cuando una función de IA falla (nunca la excepción cruda)."""
    try:
        from research.errors import friendly
        es, en = friendly(e)
    except Exception:  # noqa: BLE001
        es = en = None
    t = str(e or '')
    if not es and ('formato esperado' in t or 'no-JSON' in t):
        es = 'La IA respondió, pero no en el formato esperado. Vuelve a intentarlo en un momento.'
        en = 'The AI answered, but not in the expected format. Try again in a moment.'
    if not es and ('Expecting value' in t or 'Ningún proveedor' in t or not t.strip()):
        es = 'La IA no respondió (sin saldo o proveedor caído). Revisa 🩺 Sistema → 💰 Gasto IA.'
        en = 'The AI did not answer (no credit or provider down). Check 🩺 System → 💰 AI spend.'
    return (f'{es} · {en}' if es else f'IA falló · AI failed: {t[:160]}'), t[:160]


@app.route('/api/crypto/analyze', methods=['POST'])
@rate_limit(limit=30, window=3600)
def crypto_analyze():
    """{id?, symbol?, lang, intel?} → análisis CAUTO. Contexto: precio/mercado en
    vivo (CoinGecko) + ficha estática opcional del cliente. Cache 10 min."""
    if not _ai_configured():
        return jsonify({'ok': False, 'error': 'no AI provider configured'}), 400
    from core.providers import coingecko
    body = request.get_json(force=True, silent=True) or {}
    lang = 'en' if str(body.get('lang', 'es')).lower().startswith('en') else 'es'
    cid = coingecko.safe_coin_id(body.get('id') or '')
    sym = (body.get('symbol') or '').strip()
    intel = body.get('intel') if isinstance(body.get('intel'), dict) else None
    _key = (cid or sym or '').lower()
    if not _key:
        return jsonify({'ok': False, 'error': 'id o symbol requerido · id or symbol required'}), 400
    _ck = 'cryptoai:' + hashlib.sha256((lang + '\x00' + _key).encode('utf-8')).hexdigest()[:24]
    _hit = cache.get(_ck)
    if _hit:
        return jsonify({**_hit, 'cached': True})

    asset = None
    try:
        if cid:
            asset, _ = coingecko.get_asset(cid)
        if not asset and sym:
            data, _ = coingecko.list_markets(per_page=250, page=1)
            if isinstance(data, list):
                asset = next((r for r in data if (r.get('symbol') or '').upper() == sym.upper()), None)
    except Exception:  # noqa: BLE001
        asset = None

    _tongue = 'inglés' if lang == 'en' else 'español'
    sys = (
        'Eres un analista de criptomercados CAUTO de Khipus Finance Intelligence. '
        'NUNCA das un "compra"/"vende" tajante: das una POSTURA SUAVE con factores y un '
        'nivel de confianza, y recuerdas siempre que es análisis, no asesoría financiera. '
        'Usa los datos de mercado en vivo del contexto; no inventes cifras. '
        'Responde SOLO con un objeto JSON válido, sin markdown, con EXACTAMENTE estas claves: '
        '{"verdict": str, "confidence": int (1-5), "bull": str, "bear": str, '
        '"insights": [str], "drivers": [str], "disclaimer": str}. '
        'verdict = una frase de postura cauta. bull/bear = caso alcista/bajista en 1-2 frases. '
        'insights = 3-5 observaciones cortas. drivers = 3-5 catalizadores/factores. '
        f'Escribe TODO en {_tongue}.')
    prompt = ('Analiza este cripto con cautela.\n\nDATOS (JSON):\n'
              + json.dumps({'asset': asset, 'intel': intel}, ensure_ascii=False)[:6000])
    try:
        from core.ai import _ai_json
        parsed, model = _ai_json(sys, prompt, max_tokens=1400, tier='deep')
        if not isinstance(parsed, dict):
            raise ValueError('respuesta no-JSON')
    except Exception as e:  # noqa: BLE001
        msg, det = _ai_friendly_error(e)
        return jsonify({'ok': False, 'error': msg, 'detail': det}), 502

    def _slist(v):
        if isinstance(v, list):
            return [str(x)[:280] for x in v if str(x).strip()][:6]
        return [str(v)[:280]] if v else []
    try:
        conf = max(1, min(5, int(round(float(parsed.get('confidence', 3))))))
    except Exception:  # noqa: BLE001
        conf = 3
    disc_default = ('This is analysis, not financial advice. Crypto is highly volatile.'
                    if lang == 'en' else
                    'Esto es análisis, no asesoría financiera. El cripto es muy volátil.')
    out = {
        'ok': True,
        'verdict': str(parsed.get('verdict', ''))[:400],
        'confidence': conf,
        'bull': str(parsed.get('bull', ''))[:700],
        'bear': str(parsed.get('bear', ''))[:700],
        'insights': _slist(parsed.get('insights')),
        'drivers': _slist(parsed.get('drivers')),
        'disclaimer': str(parsed.get('disclaimer') or disc_default)[:400],
        'model': model,
        'id': (asset or {}).get('id') or cid or None,
        'symbol': (asset or {}).get('symbol') or (sym.upper() or None),
        'price': (asset or {}).get('price'),
    }
    cache.set(_ck, out, timeout=600)
    return jsonify(out)


# ── TESIS RÁPIDA (más allá del nodo, UNA respuesta de IA de nivel profundo) ──
# Limpieza 2026-10-11: antes vivía en /api/research/deep — dentro del espacio /api/research/* del equipo de
# analistas (research_bp, con evidencia y auditoría) sin ser parte de él, y la UI la llamaba "Investigación"
# igual que al equipo. Ahora tiene su propio camino y nombre.
@app.route('/api/thesis/quick', methods=['POST'])
@rate_limit(limit=20, window=3600)
def thesis_quick():
    """{id, lang} → informe estructurado que va MÁS ALLÁ de la empresa: sector,
    competidores, geopolítica, chokepoints de su cadena y una tesis. Cache 15 min."""
    from core.semantic import build_context, resolve_ids
    body = request.get_json(force=True, silent=True) or {}
    lang = 'en' if str(body.get('lang', 'es')).lower().startswith('en') else 'es'
    if not _ai_configured():
        return jsonify(_no_ai_error(lang)), 400
    raw_id = str(body.get('id') or '').strip()
    if not raw_id:
        return jsonify({'ok': False, 'error': 'id requerido · id required'}), 400
    ids = resolve_ids([raw_id])
    nid = ids[0] if ids else raw_id
    _ck = 'researchdeep:' + hashlib.sha256((lang + '\x00' + nid).encode('utf-8')).hexdigest()[:24]
    _hit = cache.get(_ck)
    if _hit:
        return jsonify({**_hit, 'cached': True})

    ctx = build_context([nid], None)
    try:
        label = (ctx['foco'][0]['empresa'].get('label') or nid) if ctx.get('foco') else nid
    except Exception:  # noqa: BLE001
        label = nid

    _tongue = 'inglés' if lang == 'en' else 'español'
    sys = (
        'Eres el analista jefe de Khipus Finance Intelligence, experto en la cadena de '
        'suministro de semiconductores, IA, espacio, energía y nuclear. Escribe una '
        'investigación PROFUNDA que va MÁS ALLÁ de la empresa foco: panorama del sector, '
        'competidores directos, exposición geopolítica, cuellos de botella (chokepoints) de '
        'su cadena, riesgos y una TESIS de inversión. Usa el contexto para nombres y '
        'relaciones reales; no inventes cifras. Responde SOLO con JSON válido (sin markdown), '
        'con EXACTAMENTE estas claves: {"thesis": str, "sector": str, "competitors": [str], '
        '"geopolitics": str, "chokepoints": [str], "risks": [str], "watch": [str], '
        '"disclaimer": str}. thesis/sector/geopolitics = 2-4 frases cada uno. Las listas: '
        f'3-6 elementos cortos. Escribe TODO en {_tongue}.')
    prompt = (f'Empresa foco: {label} (id {nid}).\n\nCONTEXTO (JSON):\n'
              + json.dumps(ctx, ensure_ascii=False)[:12000])
    try:
        from core.ai import _ai_json
        parsed, model = _ai_json(sys, prompt, max_tokens=2600, tier='deep')
        if not isinstance(parsed, dict):
            raise ValueError('respuesta no-JSON')
    except Exception as e:  # noqa: BLE001
        msg, det = _ai_friendly_error(e)
        return jsonify({'ok': False, 'error': msg, 'detail': det}), 502

    def _slist(v):
        if isinstance(v, list):
            return [str(x)[:280] for x in v if str(x).strip()][:8]
        return [str(v)[:280]] if v else []
    disc_default = ('Analysis, not financial advice.' if lang == 'en'
                    else 'Análisis, no asesoría financiera.')
    out = {
        'ok': True, 'id': nid, 'label': label, 'lang': lang, 'model': model,
        'thesis': str(parsed.get('thesis', ''))[:900],
        'sector': str(parsed.get('sector', ''))[:900],
        'competitors': _slist(parsed.get('competitors')),
        'geopolitics': str(parsed.get('geopolitics', ''))[:900],
        'chokepoints': _slist(parsed.get('chokepoints')),
        'risks': _slist(parsed.get('risks')),
        'watch': _slist(parsed.get('watch')),
        'disclaimer': str(parsed.get('disclaimer') or disc_default)[:400],
    }
    cache.set(_ck, out, timeout=900)
    return jsonify(out)


# ── Simulación POR AGENTES (motor interno) — la lógica vive en core.sim_agents
# (módulo del agente SIM). Aquí SOLO la ruta: valida el body y delega, sin romper
# el JSON si el módulo aún no existe o falla. ──────────────────────────────────
# ── GASTO DE IA (core/ai_usage.py): cuánto, en qué proveedor, en qué función y quién ──
@app.route('/api/ai/usage')
@rate_limit(limit=120, window=3600)
def ai_usage_report():
    from core import ai_usage
    try:
        days = max(1, min(int(request.args.get('days', 30)), 90))
    except (TypeError, ValueError):
        days = 30
    lang = 'en' if str(request.args.get('lang', 'es')).lower().startswith('en') else 'es'
    try:
        return jsonify(ai_usage.report(days=days, lang=lang))
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'no se pudo leer el gasto de IA', 'error_en': 'could not read AI spend',
                        'detail': f'{type(e).__name__}: {str(e)[:160]}'}), 500


@app.route('/api/ai/usage/limits', methods=['POST'])
@rate_limit(limit=30, window=3600)
@_require_pin
def ai_usage_limits():
    from core import ai_usage
    from ontology.db import ontology_available
    if not ontology_available():
        return jsonify({'error': 'Guardar límites necesita la base de datos (DATABASE_URL); mientras tanto usa '
                                 'AI_DAILY_LIMIT_USD / AI_MONTHLY_LIMIT_USD en Railway.',
                        'error_en': 'Saving limits needs the database (DATABASE_URL); meanwhile use '
                                    'AI_DAILY_LIMIT_USD / AI_MONTHLY_LIMIT_USD on Railway.'}), 503
    body = request.get_json(silent=True) or {}
    actor = str(body.get('actor') or '').strip()[:120] or 'operador'
    from core.decisions import LedgerUnavailable
    try:
        return jsonify({'ok': True, 'limits': ai_usage.save_settings(body.get('limits') or {}, actor)})
    except (TypeError, ValueError) as e:
        return jsonify({'error': f'valor inválido: {str(e)[:80]}', 'error_en': f'invalid value: {str(e)[:80]}'}), 400
    except LedgerUnavailable:          # paso 18: sin su policy.change en el libro, el cambio no se guarda
        return jsonify({'error': 'El libro de decisiones no está disponible: no se cambió nada',
                        'error_en': 'The decision ledger is unavailable: nothing was changed',
                        'code': 'ledger_unavailable'}), 503


@app.route('/api/sim/agents', methods=['POST'])
@rate_limit(limit=30, window=3600)
def sim_agents_route():
    body = request.get_json(force=True, silent=True) or {}
    scenario = str(body.get('scenario') or '').strip()
    if not scenario:
        return jsonify({'ok': False, 'error': 'scenario requerido · scenario is required'}), 400
    seeds = body.get('seeds') or []
    if not isinstance(seeds, list):
        return jsonify({'ok': False, 'error': 'seeds debe ser una lista · seeds must be a list'}), 400
    seeds = [str(s) for s in seeds if str(s).strip()][:24]
    lang = 'en' if str(body.get('lang', 'es')).lower().startswith('en') else 'es'
    try:
        from core import sim_agents
    except Exception:  # noqa: BLE001 — el módulo lo escribe el agente SIM
        return jsonify({'ok': False,
                        'error': 'Simulación por agentes no disponible · Agent simulation unavailable'}), 503
    try:
        out = sim_agents.run(scenario, seeds, lang)
        if not isinstance(out, dict):
            raise ValueError('sim_agents.run devolvió un tipo inesperado')
        out.setdefault('ok', True)
        try:                                # lote I1: whatif.agent_sim en la cola del libro (0 ms al usuario)
            from core import decision_sites
            decision_sites.agent_sim(scenario, seeds, lang, out)
        except Exception:  # noqa: BLE001
            pass
        return jsonify(out)
    except Exception as e:  # noqa: BLE001
        return jsonify({'ok': False,
                        'error': f'Error en la simulación · Simulation error: {str(e)[:180]}'}), 500


@app.route('/api/earnings/<ticker>')
@rate_limit(limit=120, window=60)
@cache.cached(timeout=3600)
def earnings(ticker):
    if not FINNHUB:
        return jsonify({'earningsCalendar': []})
    ticker = _safe_ticker(ticker)
    if not ticker:
        return jsonify({'earningsCalendar': []})
    frm = (date.today() - timedelta(days=120)).isoformat()
    to = (date.today() + timedelta(days=120)).isoformat()
    data, err = _safe_get(
        f'https://finnhub.io/api/v1/calendar/earnings?symbol={ticker}'
        f'&from={frm}&to={to}&token={FINNHUB}')
    if err:
        return _degraded(jsonify({'earningsCalendar': []}))
    return jsonify(data)


# ----------------------------------------------------------------------------
# FMP — fundamentales, precio objetivo, ratings, insiders
# ----------------------------------------------------------------------------
@app.route('/api/fundamentals/<ticker>')
@rate_limit(limit=120, window=60)
def fundamentals(ticker):
    ticker = _safe_ticker(ticker)
    if not ticker:
        return jsonify({'error': 'invalid ticker'}), 400
    # Cache manual: no cachear si los datos vienen vacíos (evita envenenar 24h con errores de rate-limit)
    cache_key = f'fund2_{ticker}'   # v2: + marketCapB (la v1 cacheada 24 h no la traía)
    hit = cache.get(cache_key)
    if hit is not None:
        return jsonify(hit)

    metrics = []
    targets = []
    ratings = []
    # Capitalización EN VIVO (miles de millones USD). El catálogo solo la trae
    # para ~110 de ~620 cotizadas, y sin ella la UI decía "Privada" a bancos
    # como Mizuho. US → Finnhub (ya viene en /stock/metric, que se pedía y se
    # descartaba); resto del mundo → perfil de FMP convertido a USD.
    mcap_b, mcap_src = None, None
    # Métricas (P/E, EV/EBITDA): Finnhub /stock/metric disponible en plan gratuito
    if FINNHUB:
        fh, fh_err = _safe_get(f'https://finnhub.io/api/v1/stock/metric?symbol={ticker}&metric=all&token={FINNHUB}')
        log.debug('fh err=%s type=%s', fh_err, type(fh).__name__)
        if fh and isinstance(fh.get('metric'), dict):
            m = fh['metric']
            pe = m.get('peTTM') or m.get('peBasicExclExtraTTM')
            ev = m.get('evEbitdaTTM') or m.get('evEbitdaAnnual')
            metrics = [{'peRatio': round(float(pe), 2) if pe else None,
                        'enterpriseValueOverEBITDA': round(float(ev), 2) if ev else None}]
            try:
                mc = m.get('marketCapitalization')   # millones USD
                if mc and float(mc) > 0:
                    mcap_b, mcap_src = round(float(mc) / 1000.0, 2), 'finnhub'
            except (TypeError, ValueError):
                pass
    if mcap_b is None and FMP:
        prof, _ = _safe_get(f'https://financialmodelingprep.com/stable/profile?symbol={ticker}&apikey={FMP}')
        p0 = prof[0] if isinstance(prof, list) and prof and isinstance(prof[0], dict) else None
        if p0:
            try:
                mc = float(p0.get('marketCap') or 0)
                from core.quotes import _fx_to_usd
                rate = _fx_to_usd((p0.get('currency') or 'USD').upper())
                if mc > 0 and rate:
                    mcap_b, mcap_src = round(mc * rate / 1e9, 2), 'fmp'
            except (TypeError, ValueError):
                pass
    # Precio objetivo y ratings de analistas: FMP (plan actual soporta estos endpoints)
    if FMP:
        targets, _ = _safe_get(f'https://financialmodelingprep.com/stable/price-target-consensus?symbol={ticker}&apikey={FMP}')
        grades_raw, _ = _safe_get(f'https://financialmodelingprep.com/stable/grades?symbol={ticker}&limit=20&apikey={FMP}')
        if isinstance(grades_raw, list) and grades_raw:
            strong_buy_kw = {'strong buy'}
            buy_kw = {'buy', 'outperform', 'overweight', 'accumulate', 'add', 'positive'}
            strong_sell_kw = {'strong sell'}
            sell_kw = {'sell', 'underperform', 'underweight', 'reduce', 'negative'}
            b = sb = s = ss = h = 0
            for g in grades_raw:
                grade = (g.get('newGrade') or '').lower()
                if any(k in grade for k in strong_buy_kw): sb += 1
                elif any(k in grade for k in buy_kw): b += 1
                elif any(k in grade for k in strong_sell_kw): ss += 1
                elif any(k in grade for k in sell_kw): s += 1
                else: h += 1
            ratings = [{'analystRatingsBuy': b, 'analystRatingsStrongBuy': sb,
                        'analystRatingsSell': s, 'analystRatingsStrongSell': ss,
                        'analystRatingsHold': h}]
    if mcap_b is None:
        # tercera vía: Yahoo (cubre Tokio, Hong Kong, Europa… que el plan
        # gratuito de FMP no). Devuelve USD o None; nunca inventa.
        from core.quotes import fetch_market_cap_yahoo
        y = fetch_market_cap_yahoo(ticker)
        if y:
            mcap_b, mcap_src = y, 'yahoo'
    result = {'metrics': metrics, 'priceTarget': targets or [], 'ratings': ratings,
              'marketCapB': mcap_b, 'marketCapSource': mcap_src}
    # Solo cachear si obtuvimos algo — errores transitorios no deben quedarse 24h
    if metrics or targets or ratings or mcap_b:
        cache.set(cache_key, result, timeout=86400)
    return jsonify(result)


@app.route('/api/insiders/<ticker>')
@rate_limit(limit=120, window=60)
@cache.cached(timeout=86400)
def insiders(ticker):
    ticker = _safe_ticker(ticker)
    if not ticker:
        return jsonify([])
    if not FMP:
        return jsonify([])
    data, err = _safe_get(f'https://financialmodelingprep.com/stable/insider-trading?symbol={ticker}&limit=10&apikey={FMP}')
    if err or not isinstance(data, list):
        return _degraded(jsonify([]))
    return jsonify(data)


# ----------------------------------------------------------------------------
# IA — análisis de empresa / impacto de cadena / síntesis de noticias.
# La cascada multi-proveedor (Claude→Gemini→NVIDIA) vive en core/ai.py,
# compartida con los agentes de la ontología. Aquí solo quedan las rutas.
# ----------------------------------------------------------------------------
@app.route('/api/ai/analyze', methods=['POST'])
@rate_limit(limit=30, window=3600)   # 30 AI analyses per hour per IP
def ai_analyze():
    if not _ai_configured():
        return jsonify({'error': 'no AI provider configured (Claude/Gemini/NVIDIA)'}), 400
    data = request.get_json(force=True, silent=True) or {}
    # IA híbrida: el cliente puede pedir tier='deep' (Sonnet 5) para análisis
    # que importan (tesis, X-Ray/SecondBrain); todo lo demás queda 'fast' (Haiku).
    tier = 'deep' if str(data.get('tier', '')).strip().lower() == 'deep' else 'fast'
    # Clamp max_tokens to avoid runaway costs (deep permite más presupuesto)
    max_tok = min(int(data.get('max_tokens', 1000)), 3000 if tier == 'deep' else 2000)
    # caché 30 min por (tier+system+prompt): el mismo análisis no paga otra llamada IA
    _ck = 'aian:' + hashlib.sha256(
        (tier + '\x00' + str(data.get('system', '')) + '\x00' + str(data.get('prompt', ''))).encode('utf-8')
    ).hexdigest()[:24]
    _hit = cache.get(_ck)
    if _hit:
        return jsonify({'result': _hit['result'], 'model': _hit['model'], 'cached': True})
    try:
        text, model = _ai_complete(
            data.get('system', ''),
            data.get('prompt', ''),
            max_tok,
            tier=tier,
        )
        cache.set(_ck, {'result': text, 'model': model}, timeout=1800)
        return jsonify({'result': text, 'model': model})
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200]}), 500


# ── Khipu Canvas — AI-generated chart specs (Fase 1) ────────────────────────
_CANVAS_SYSTEM = """\
You are Khipus Finance Intelligence's Canvas AI — an expert at semiconductor / AI / space supply chain analytics.
Given a user query and a JSON context with node data and market quotes, produce a single-screen
data visualization spec. Respond ONLY with valid JSON — no markdown fences, no explanation.

Supported types and their data schemas:
• bar       – data:[{label,value,color?}]                 config:{unit?}
• grouped   – data:[{label:<metric or category>,values:[n per series],unit?}]  config:{series_labels:[…]}
• line      – data:[{label,values:[n,…],color?}]          config:{unit?,series_labels:[…],labels:[x labels…]}
• kpi       – data:[{label,value,unit?,sub?}]  (1-6 tiles)  config:{}
• donut     – data:[{label,value,color?}]  (≤6 slices)      config:{unit?}
• treemap   – data:[{label,value,color?}]                   config:{unit?}
• histogram – data:[{label:<range>,value:<count>}]          config:{x_label?}
• scatter   – data:[{label,x,y,color?}]                     config:{x_label,y_label}
• bubble    – data:[{label,x,y,r,color?}]                   config:{x_label,y_label,r_label}
• heatmap   – data:[{row,col,value}]                        config:{rows:[…],cols:[…],unit?}
• radar     – data:[{label,values:[0-100,…]}]               config:{axes:[…]}  (≤3 series, 4-8 axes)
• table     – data:[{col:val,…}]                            config:{columns:[…]}

Always respond with exactly:
{"type":"<type>","title":"<concise title>","subtitle":"<1 sentence insight>","data":[…],"config":{…},
 "source":"<short 'how computed' line: which context fields you used>"}

CHART-TYPE CRITERION (follow it; the server re-checks it):
  · compare few items (2-6): bar sorted (one metric) or grouped (several metrics); radar only if asked; table if >6 items.
  · time / trend: line (bar only for annual amounts that can be negative: capex, free cash flow, growth %).
  · ranking / top N: bar, sorted descending, max 20.
  · composition / share of a whole: donut if ≤6 slices, otherwise treemap.
  · distribution: histogram of pre-binned counts.
  · relationship between two metrics: scatter (bubble if a third metric sizes the dots).
  · a single number: kpi.  · detailed multi-attribute: table.  · country × sector: heatmap.
  If the user asked for a specific type, honor it unless the data shape makes it unreadable.
  If a PARSED REQUEST block is present, it is the app router's reading of the query — use its
  intent, companies and metrics.

Units: put the unit in config.unit (or per item) — "$B" (USD billions), "%", "$" (price), "x", "NRS", "year", "".
Values are plain numbers in that unit (62 not "62%").

DATA RULES (critical — investors rely on this):
- Use ONLY numbers present in the context. NEVER invent prices, market caps, revenues, margins or counts.
- If the context lacks the requested metric, chart the closest metric you DO have and say so in subtitle
  (e.g. "No P/E in the data — showing margin and market cap"), or use a table with "—" for missing values.
- nodes[].nrs is a 0-100 RISK score (higher = riskier). nodes[].margin is a fraction (0.62 = 62 %).
  nodes[].mktcap_b and revenue_b are USD billions; employees and founded are plain numbers.
- context.live = {SYMBOL:{price,change_pct}} holds REAL live prices — use them for price questions.
- sector_summary has catalog aggregates per category.
- Colors palette: #60a5fa #34d399 #f59e0b #f87171 #a78bfa #38bdf8 #fb923c #4ade80
"""

_CV_PALETTE = ['#60a5fa','#34d399','#f59e0b','#f87171','#a78bfa','#38bdf8','#fb923c','#4ade80']

@app.route('/api/canvas/generate', methods=['POST'])
@rate_limit(limit=60, window=3600)
def canvas_generate():
    if not _ai_configured():
        return jsonify({'error': 'no AI provider configured (Claude/Gemini/NVIDIA)'}), 400
    body = request.get_json(force=True, silent=True) or {}
    query = str(body.get('query', ''))[:500].strip()
    if not query:
        return jsonify({'error': 'query is required'}), 400
    ctx = body.get('context', {})
    if not isinstance(ctx, dict):
        ctx = {}
    nodes_raw = [n for n in (ctx.get('nodes') or []) if isinstance(n, dict)]
    quotes_raw = ctx.get('quotes') or {}
    # ROUTER (2026-10-02): el cliente manda la consulta ya parseada
    # (intención, empresas, métricas) → la IA elige el gráfico con el MISMO
    # criterio y validate_spec corrige el tipo si no encaja.
    from core.canvas_spec import sanitize_hints, hints_prompt, validate_spec
    hints = sanitize_hints(body.get('hints'))

    # ── ADELGAZAR EL CONTEXTO (fix "los gráficos tardan full") ───────────────
    # Antes: las 555 empresas completas viajaban a la IA (~150 KB de prompt →
    # generación lenta). Ahora (Capa 2): si la consulta menciona empresas, solo
    # esas + un resumen por sector; si no, el top relevante + el resumen.
    # Los pedidos comunes ya ni llegan aquí (engine/localcharts.js, 0 ms).
    _clip = lambda n: {k: n.get(k) for k in ('id', 'label', 'cat', 'mkt', 'margin',  # noqa: E731
                                             'growth', 'port', 'country', 'preipo', 'nrs',
                                             'mktcap_b', 'revenue_b', 'employees', 'founded')
                       if n.get(k) is not None}
    mentioned = []
    try:
        from core.semantic import extract_companies
        mset = set(extract_companies(query, limit=12))
        if mset:
            mentioned = [n for n in nodes_raw if n.get('id') in mset]
    except Exception:  # noqa: BLE001
        pass
    _hint_ids = [e['id'] for e in hints.get('entities', [])]
    if _hint_ids:
        _have = {n.get('id') for n in mentioned}
        mentioned += [n for n in nodes_raw if n.get('id') in _hint_ids and n.get('id') not in _have]
    if mentioned and hints.get('intent') not in ('rank', 'distribution', 'relationship', 'composition', 'cross'):
        nodes_compact = [_clip(n) for n in mentioned[:40]]
    elif mentioned or hints.get('metrics'):
        # consultas panorámicas: las mencionadas + el top por la métrica pedida
        _mk = {'nrs': 'nrs', 'margin': 'margin', 'mktcap': 'mktcap_b', 'revenue': 'revenue_b',
               'employees': 'employees'}.get((hints.get('metrics') or ['nrs'])[0], 'nrs')
        _srt = sorted([n for n in nodes_raw if n.get(_mk) is not None], key=lambda n: -(n.get(_mk) or 0))
        _ranked = _srt[:50] + [n for n in _srt[-25:] if n not in _srt[:50]]   # ambos extremos (mayor y menor)
        _ids = {n.get('id') for n in mentioned}
        nodes_compact = [_clip(n) for n in (mentioned[:30] + [n for n in _ranked if n.get('id') not in _ids])[:90]]
    else:
        ranked = sorted(nodes_raw, key=lambda n: -(n.get('nrs') or 0))[:60]
        ranked += [n for n in nodes_raw if n.get('port') and n not in ranked][:20]
        nodes_compact = [_clip(n) for n in ranked[:80]]
    # resumen agregado por sector (para consultas panorámicas sin 555 filas)
    sector_summary = {}
    for n in nodes_raw:
        s = n.get('cat') or '?'
        agg = sector_summary.setdefault(s, {'n': 0, 'nrs_sum': 0, 'nrs_n': 0, 'margin_sum': 0, 'margin_n': 0})
        agg['n'] += 1
        if n.get('nrs') is not None:
            agg['nrs_sum'] += n['nrs']; agg['nrs_n'] += 1
        if n.get('margin') is not None:
            agg['margin_sum'] += n['margin']; agg['margin_n'] += 1
    sector_summary = {k: {'empresas': v['n'],
                          'nrs_prom': round(v['nrs_sum'] / v['nrs_n'], 1) if v['nrs_n'] else None,
                          'margen_prom': round(v['margin_sum'] / v['margin_n'], 2) if v['margin_n'] else None}
                      for k, v in sector_summary.items()}
    # quotes: solo de las empresas incluidas
    _tks = {n.get('mkt') for n in nodes_compact if n.get('mkt')}
    quotes_raw = {t: q for t, q in quotes_raw.items() if t in _tks}
    live_raw = ctx.get('live') or {}
    # caché por consulta (30 min): la misma pregunta no debe pagar otra llamada
    # de IA de varios segundos. Si hay precios en vivo en juego, TTL corto (2 min).
    _ck = 'canvas2:' + hashlib.sha256((query.lower() + '\x00' + json.dumps(hints, sort_keys=True)).encode('utf-8')).hexdigest()[:24]
    _hit = cache.get(_ck)
    if _hit:
        return jsonify({'spec': _hit['spec'], 'model': _hit['model'], 'cached': True})
    ctx_str = json.dumps({'nodes': nodes_compact, 'sector_summary': sector_summary,
                          'quotes': quotes_raw, 'live': live_raw,
                          'selected': ctx.get('selected_id')},
                         ensure_ascii=False)
    _hp = hints_prompt(hints)
    prompt = f'USER QUERY: {query}\n\n' + (_hp + '\n\n' if _hp else '') + f'CONTEXT:\n{ctx_str}'
    try:
        # Canvas IA = análisis que importa → tier 'deep' (Sonnet 5)
        text, model = _ai_complete(_CANVAS_SYSTEM, prompt, max_tokens=1600, tier='fast')
        # extrae el JSON aunque venga con fences o texto alrededor
        spec = _extract_json(text)
        # CRITERIO DE GRÁFICO + limpieza (alias de tipos, pie de 40 porciones →
        # barras/treemap, línea sin eje de tiempo → barras, barras ordenadas…)
        try:
            spec, _fixes = validate_spec(spec, hints, query)
        except ValueError as ve:
            return jsonify({'error': f'invalid chart spec: {ve}', 'raw': (text or '')[:300]}), 502
        cache.set(_ck, {'spec': spec, 'model': model},
                  timeout=(120 if live_raw else 1800))
        return jsonify({'spec': spec, 'model': model})
    except json.JSONDecodeError:
        return jsonify({'error': 'model returned non-JSON', 'raw': (text or '')[:400]}), 502
    except Exception as e:   # noqa: BLE001
        return jsonify({'error': str(e)[:200]}), 500


# (/api/ai/command — el "Command Center" viejo — se borró en la limpieza 2026-10-11: ningún
#  cliente lo llamaba; todo pedido libre va a /api/khipu/chat, core/khipu_chat.py)


# ----------------------------------------------------------------------------
# Marketstack proxy (compatibilidad con v7)
# ----------------------------------------------------------------------------
@app.route('/api/marketstack')
@rate_limit(limit=60, window=60)
@cache.cached(timeout=3600, query_string=True)
def marketstack_proxy():
    if not MSTACK:
        return jsonify({'error': 'no MARKETSTACK_KEY'}), 400
    symbols = ','.join(s for s in (_safe_ticker(t) for t in request.args.get('symbols', '').split(',')) if s)
    from_date = request.args.get('date_from', (date.today() - timedelta(days=9)).isoformat())
    data, err = _safe_get(
        f'https://api.marketstack.com/v2/eod?access_key={MSTACK}'
        f'&symbols={symbols}&date_from={from_date}&limit=1000&sort=DESC',
        timeout=12)
    if err:
        return jsonify({'error': err}), 502
    return jsonify(data)


@app.route('/api/ipo_calendar')
@rate_limit(limit=60, window=60)
@cache.cached(timeout=3600)
def ipo_calendar():
    """IPO calendar from Finnhub — last 90 days + next 30 days"""
    if not FINNHUB:
        return jsonify({'error': 'no FINNHUB_KEY'}), 400
    from_d = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    to_d   = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    data, err = _safe_get(
        f'https://finnhub.io/api/v1/calendar/ipo?from={from_d}&to={to_d}&token={FINNHUB}',
        timeout=8)
    if err:
        return jsonify({'error': err}), 502
    return jsonify(data)


# ════════════════════════════════════════════════════════════════════════════
# KHIPU FINANCE v1 — Backend ampliado
# Space APIs · GDELT · SEC EDGAR · Khipu voice · API pública JWT
# ════════════════════════════════════════════════════════════════════════════

# ── Space APIs (Launch Library 2 — gratis) ──────────────────────────────────
@app.route('/api/space/launches')
@rate_limit(limit=60, window=60)
def space_launches():
    """Próximos lanzamientos espaciales, mapeados a nodos de Khipu. Blindado para
    la demo: timeout corto + respaldo vacío si Launch Library está lento/caído (una
    caché fría podía tardar mucho y bloquear la pestaña Espacio). Caché manual para
    no quedar pegado en el respaldo."""
    ck = 'space_launches_v2'
    hit = cache.get(ck)
    if hit is not None:
        return jsonify(hit)
    data, err = _safe_get(
        'https://ll.thespacedevs.com/2.2.0/launch/upcoming/?limit=10&format=json', timeout=8)
    if err or not isinstance(data, dict):
        cache.set(ck, [], timeout=90)   # respaldo breve: no bloquear, reintentar pronto
        return jsonify([])
    launches = data.get('results', [])

    def khipu_nodes(launch):
        name = ((launch.get('name', '') or '') +
                (launch.get('launch_service_provider') or {}).get('name', '')).lower()
        nodes = []
        if 'spacex' in name:    nodes.append('SpaceX')
        if 'rocket lab' in name: nodes.append('RocketLab')
        if 'starlink' in name:  nodes.extend(['SpaceX', 'T_Mobile'])
        if 'planet' in name:    nodes.append('PlanetLabs')
        if 'ast' in name or 'bluebird' in name: nodes.append('AST_SpaceMobile')
        if 'oneweb' in name:    nodes.append('EutelsatOneWeb')
        return list(set(nodes))

    return jsonify([{
        'id': l.get('id'), 'name': l.get('name'), 'net': l.get('net'),
        'provider': (l.get('launch_service_provider') or {}).get('name'),
        'rocket': (l.get('rocket') or {}).get('configuration', {}).get('name'),
        'status': (l.get('status') or {}).get('name'),
        'probability': l.get('probability'),
        'khipu_nodes': khipu_nodes(l),
    } for l in launches])


# ── CelesTrak TLE — satélites reales para el Space Monitor ───────────────────
# Toda la conversación con CelesTrak vive en core/celestrak.py (copia por grupo,
# ≤1 descarga por grupo cada 2 h, pausa ante bloqueo/límite, ronda ≤20 s): antes
# esta ruta pedía los 11 grupos en serie con 12 s cada uno (~132 s colgada con
# CelesTrak bloqueando → globo SIN satélites) y _space_constellations los volvía
# a descargar por su cuenta (lo que hace que CelesTrak bloquee la IP).
from core import celestrak as _celestrak  # noqa: E402

_SAT_GROUPS = _celestrak.GROUPS
_parse_tle_text = _celestrak.parse_tle_text
_fallback_tle = _celestrak.fallback_tle


@app.route('/api/space/tle')
@rate_limit(limit=120, window=3600)   # ya no cuesta descargas: sale de la copia en memoria
def space_tle():
    """Satélites reales por constelación (CelesTrak). Muestrea para rendimiento
    pero reporta los conteos REALES (con `as_of`; `stale` = copia de más de 6 h).
    Sin ninguna copia: órbitas de REFERENCIA con source='fallback' (la UI lo dice)."""
    data = _celestrak.payload()
    resp = jsonify(data)
    if data.get('source') == 'fallback' or data.get('stale'):
        return _degraded(resp)
    resp.headers['Cache-Control'] = 'public, max-age=600'
    return resp


# Pisos de respaldo por constelación (aprox. 2026): si CelesTrak falla en un
# grupo concreto (rate-limit), usamos este mínimo para que Starlink NO quede en 0
# ni "desaparezca" del resumen de texto (marcado live=False: cifra de REFERENCIA).
_SAT_FALLBACK = {'Starlink': 8000, 'OneWeb': 648, 'Planet Labs': 190, 'Spire Global': 70,
                 'Iridium NEXT': 80, 'Globalstar': 28, 'SES / O3b': 68, 'GPS': 31,
                 'Galileo': 30, 'BeiDou': 50, 'Estaciones (ISS/CSS)': 20}


def _space_constellations():
    """[(label, count, live), …] satélites por constelación para el Khipu de TEXTO.
    Lee la MISMA copia que /api/space/tle (core/celestrak: sin descargas propias);
    un grupo sin copia usa su piso de respaldo con live=False."""
    real = _celestrak.counts()
    out = []
    for _group, label, _node, _color in _SAT_GROUPS:
        n = real.get(label, 0)
        live = bool(n)
        if not n:
            n = _SAT_FALLBACK.get(label, 0)
        if n:
            out.append((label, n, live))
    return out


def _space_facts_str():
    cons = _space_constellations()
    total = sum(n for _, n, _l in cons)
    ref = [lbl for lbl, _, lv in cons if not lv]
    return (f'Total aproximado: {total} satélites rastreados en órbita. '
            + ' · '.join(f'{lbl}: {n}' + ('' if lv else ' (cifra de referencia, NO en vivo)')
                         for lbl, n, lv in cons)
            + ' (fuente CelesTrak, se actualiza a diario'
            + (f'; CelesTrak no respondió para {", ".join(ref)} — dilo si citas esas cifras' if ref else '')
            + ').')


# ── GDELT News (gratis, global, multi-idioma) ────────────────────────────────
@app.route('/api/news/gdelt/<company_name>')
@rate_limit(limit=60, window=60)
def news_gdelt(company_name):
    # Caché MANUAL de 5 min solo de éxitos (antes 30 min, y cacheaba también
    # los fallos de GDELT: el Dossier "en vivo" no veía noticias nuevas y un
    # corte de GDELT quedaba envenenado media hora).
    from urllib.parse import quote as _urlq
    company_name = re.sub(r'[^A-Za-z0-9 ._-]', '', company_name)[:60]
    _ck = f'gdelt_{company_name.lower()}'
    _hit = cache.get(_ck)
    if _hit is not None:
        return jsonify(_hit)
    url = (f'https://api.gdeltproject.org/api/v2/doc/doc?query={_urlq(company_name)}'
           f'&mode=artlist&maxrecords=20&format=json&sort=datedesc')
    data, err = _safe_get(url, timeout=12)
    if err or not isinstance(data, dict):
        return jsonify([])
    out = [{
        'headline': a.get('title'), 'url': a.get('url'), 'source': a.get('domain'),
        'datetime': a.get('seendate'), 'language': a.get('language'),
        'sentiment': float(a.get('tone', 0) or 0), 'source_api': 'GDELT',
    } for a in (data.get('articles', []) or [])[:20]]
    cache.set(_ck, out, timeout=300)
    return jsonify(out)


# ── SEC EDGAR (financieros oficiales, gratis) ────────────────────────────────
_CIK_MAP = {
    'NVDA': '0001045810', 'INTC': '0000050863', 'AMD': '0000002488',
    'TSMC': '0001046179', 'AMAT': '0000006951', 'KLAC': '0000319201',
    'LRCX': '0000707549', 'ASML': '0000937556', 'QCOM': '0000804328',
    'AVGO': '0001730168', 'TXN': '0000097476', 'MU': '0000723125',
    'MRVL': '0001058057', 'ADI': '0000006951', 'MCHP': '0000827054',
    'ON': '0001285785', 'STM': '0000928072', 'NXPI': '0001413447',
    'SWKS': '0000004127', 'QRVO': '0001604778', 'MPWR': '0001280452',
    'WOLF': '0000895419', 'AMBA': '0001280263', 'SLAB': '0001060349',
    'IBM': '0000051143', 'MSFT': '0000789019', 'AMZN': '0001018724',
    'GOOGL': '0001652044', 'META': '0001326801', 'AAPL': '0000320193',
    'ORCL': '0001341439', 'CRM': '0001108524', 'NOW': '0001373715',
    'SNOW': '0001639825', 'DDOG': '0001568385', 'NET': '0001477333',
    'PLTR': '0001321655', 'AI': '0001577552', 'PATH': '0001620459',
    'IONQ': '0001838359', 'RGTI': '0001737287', 'QUBT': '0001809987',
    'RKLB': '0001819615', 'ASTS': '0001780787', 'SPCE': '0001706946',
    'IREN': '0001527166', 'CORZ': '0001836935',
    'TSM': '0001046179', 'SSNLF': '0000066740', 'SIEGY': '0000073309',
    'FANUY': '0000315189',
    # Legacy entries preserved
    'TSLA': '1318605', 'ANET': '1313925', 'VRT': '1837240',
    'CRWV': '1971311', 'IRDM': '1418819', 'GSAT': '1366868', 'PL': '1836833', 'MP': '1801368',
    'MBLY': '1910139', 'TEM': '1717115', 'MSCI': '1408198', 'KTOS': '1069258',
}


@app.route('/api/dossier/<ticker>')
@rate_limit(limit=30, window=60)
def dossier(ticker):
    """Dossier de 5-6 años para la pestaña Análisis (app.html
    `_dossierRenderPanels`): ingresos, dilución, FCF, valuación, balance,
    márgenes, ROE/ROIC — en MILES DE MILLONES USD y %.

    2026-09-28: antes usaba FMP /api/v3 (el plan de producción responde 402) y
    el cliente caía SIEMPRE a un dossier INVENTADO. Ahora usa la misma
    cascada honesta que /api/findossier (core/company_data). `synthetic` es
    SIEMPRE False. Sin datos → 200 {available:false, reason, ticker}: el
    cliente muestra un mensaje honesto, jamás números inventados."""
    ticker = _safe_ticker(ticker)
    if not ticker:
        return jsonify({'error': 'invalid ticker'}), 400
    from core.company_data import get_annual_financials, to_dossier
    try:
        fin = get_annual_financials(ticker, fmp_key=FMP, av_key=AV_KEY)
    except Exception as e:  # noqa: BLE001
        log.warning('dossier %s: %s', ticker, type(e).__name__)
        fin = {'available': False, 'reason': 'error interno al consultar las fuentes',
               'reason_en': 'internal error while querying the sources'}
    return jsonify(to_dossier(fin, ticker))


@app.route('/api/market/live_caps')
@rate_limit(limit=60, window=300)
def market_live_caps():
    """Capitalización + precio EN VIVO de TODAS las cotizadas del grafo (lote
    Yahoo, caché 15 min, refresco en segundo plano). El cliente pisa con esto
    el catálogo estático (NODE_META.mktcap_b). Pedido: "que todo esté en vivo"."""
    from core.live_caps import get_caps
    return jsonify(get_caps())


@app.route('/api/market/live_fundamentals')
@rate_limit(limit=60, window=300)
def market_live_fundamentals():
    """Fundamentales EN VIVO (margen, crecimiento, ingresos 12 m, empleados) de todas las cotizadas,
    refrescados por tandas en segundo plano (core/live_fundamentals). El cliente los aplica a todo el catálogo."""
    from core.live_fundamentals import get_all
    return jsonify(get_all())


@app.route('/api/company/live/<ticker>')
@rate_limit(limit=120, window=60)
def company_live(ticker):
    """Perfil EN VIVO de cualquier empresa cotizada (pedido 2026-09-28: "que la
    info se actualice en vivo"): precio y % del día, capitalización en USD,
    empleados, ingresos TTM, márgenes, P/E, rango 52 semanas, precio objetivo.
    Yahoo quoteSummary → Finnhub (EE.UU.) → Yahoo chart; caché 90 s en
    core/company_data. Responde 200 SIEMPRE con available true/false."""
    ticker = _safe_ticker(ticker)
    if not ticker:
        return jsonify({'error': 'invalid ticker', 'available': False}), 400
    from core.company_data import get_live_profile
    try:
        prof = get_live_profile(ticker, finnhub_key=FINNHUB)
    except Exception as e:  # noqa: BLE001
        log.warning('company_live %s: %s', ticker, type(e).__name__)
        prof = {'available': False, 'source': None, 'symbol': ticker,
                'reason': 'error interno al consultar las fuentes',
                'reason_en': 'internal error while querying the sources'}
    return jsonify(prof)


@app.route('/api/company/valuation/<path:name>')
@rate_limit(limit=60, window=60)
def company_valuation_news(name):
    """Valuación de una PRIVADA según los titulares recientes (GDELT): la cifra
    citada, medio, fecha y si es ronda cerrada o negociación. Pedido
    2026-09-28: "OpenAI dice $500B y está por $1T — que siempre sea en vivo"."""
    from core.company_data import get_valuation_news
    try:
        return jsonify(get_valuation_news(name))
    except Exception as e:  # noqa: BLE001
        log.warning('company_valuation %s: %s', name[:40], type(e).__name__)
        return jsonify({'available': False, 'mentions': [],
                        'reason': 'error interno', 'reason_en': 'internal error'})


# ── SEC 10-K Research — síntesis del filing con Claude (Fase 2) ───────────────
_SEC_UA = os.getenv('SEC_USER_AGENT', 'Khipu Finance research@khipu.finance')
_SEC_TICKERS = {'data': None, 'ts': 0.0}


def _resolve_cik(ticker):
    t = (ticker or '').upper()
    if t in _CIK_MAP:
        return _CIK_MAP[t].zfill(10)
    now = time.time()
    if not _SEC_TICKERS['data'] or now - _SEC_TICKERS['ts'] > 86400:
        try:
            r = requests.get('https://www.sec.gov/files/company_tickers.json',
                             headers={'User-Agent': _SEC_UA}, timeout=12)
            if r.ok:
                m = {}
                for row in r.json().values():
                    m[str(row.get('ticker', '')).upper()] = str(row.get('cik_str', '')).zfill(10)
                _SEC_TICKERS['data'] = m
                _SEC_TICKERS['ts'] = now
        except Exception:  # noqa: BLE001
            pass
    return (_SEC_TICKERS['data'] or {}).get(t)


def _strip_html(html):
    html = re.sub(r'(?is)<(script|style|table)[^>]*>.*?</\1>', ' ', html)
    text = re.sub(r'(?s)<[^>]+>', ' ', html)
    text = re.sub(r'&#160;|&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    return re.sub(r'[ \t ]+', ' ', re.sub(r'\n\s*\n+', '\n', text)).strip()


def _extract_section(text, markers, length=3500):
    low = text.lower()
    for mk in markers:
        i = low.find(mk.lower())
        if i >= 0:
            return text[i:i + length]
    return ''


@app.route('/api/company/research/<ticker>')
@rate_limit(limit=15, window=3600)
@cache.cached(timeout=86400)
def company_research(ticker):
    """Descarga el 10-K/20-F más reciente de SEC EDGAR y Claude lo sintetiza."""
    if not _ai_configured():
        return jsonify({'error': 'no AI provider configured (Claude/Gemini/NVIDIA)'}), 400
    safe = _safe_ticker(ticker)
    if not safe:
        return jsonify({'error': 'invalid ticker'}), 400
    cik = _resolve_cik(safe)
    if not cik:
        return jsonify({'error': f'No SEC filings found for {safe} (foreign/private?)'}), 404
    try:
        sub = requests.get(f'https://data.sec.gov/submissions/CIK{cik}.json',
                           headers={'User-Agent': _SEC_UA}, timeout=15)
        if not sub.ok:
            return jsonify({'error': f'SEC submissions HTTP {sub.status_code}'}), 502
        recent = sub.json().get('filings', {}).get('recent', {})
        forms = recent.get('form', [])
        idx = next((i for i, f in enumerate(forms) if f in ('10-K', '20-F')), None)
        if idx is None:
            return jsonify({'error': f'No 10-K/20-F on file for {safe}'}), 404
        accession = recent['accessionNumber'][idx].replace('-', '')
        primary = recent['primaryDocument'][idx]
        form_type = forms[idx]
        fdate = recent['filingDate'][idx]
        doc_url = f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary}'
        doc = requests.get(doc_url, headers={'User-Agent': _SEC_UA}, timeout=20)
        if not doc.ok:
            return jsonify({'error': f'SEC document HTTP {doc.status_code}'}), 502
        text = _strip_html(doc.text)
        business = _extract_section(text, ['Item 1. Business', 'Item 1.Business', 'Overview'], 2800)
        risks = _extract_section(text, ['Item 1A. Risk Factors', 'Risk Factors'], 4200)
        mdna = _extract_section(text, ['Item 7. Management', "Management's Discussion", 'Results of Operations'], 4200)
        if not (risks or mdna or business):
            return jsonify({'error': 'No se pudieron extraer secciones del filing',
                            'source_url': doc_url}), 502
        prompt = (f'Analiza el filing {form_type} de {safe} ({fdate}). Responde en español, conciso.\n\n'
                  f'NEGOCIO:\n{business}\n\nFACTORES DE RIESGO:\n{risks}\n\nMD&A:\n{mdna}')
        system = (
            'Eres un analista financiero senior. A partir de las secciones del filing SEC, '
            'responde SOLO con JSON válido (sin markdown):\n'
            '{"resumen":["3 bullets del negocio"],'
            '"riesgos":[{"riesgo":"...","severidad":"Alta|Media|Baja"}],'
            '"tendencias":["bullets de MD&A: ingresos, márgenes, guidance"],'
            '"confianza":{"score":0-10,"justificacion":"1 frase"}}')
        out, model = _ai_complete(system, prompt, max_tokens=1400)
        cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', (out or '').strip())
        try:
            analysis = json.loads(cleaned)
        except json.JSONDecodeError:
            analysis = {'resumen': [out[:600] if out else 'Sin análisis'], 'riesgos': [],
                        'tendencias': [], 'confianza': {}}
        return jsonify({'ticker': safe, 'form_type': form_type, 'filing_date': fdate,
                        'analysis': analysis, 'source_url': doc_url, 'model': model})
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200]}), 500


# ── Grafo de Conocimiento Temporal — /api/grafo/estado ──────────────────────────────────────────────────────────
# El panel funciona 100% en el cliente (deriva hechos de NODES/LINKS/PREIPO) y la memoria temporal con historia vive
# en Postgres (/api/ontology/graph?as_of=, G(t, κ)). Neo4j y su carga masiva (POST /api/grafo/seed) se RETIRARON el
# 2026-10-13 (decisión #6 de Fabrizio: nadie lo leía). Este estado queda para la insignia del Grafo Temporal y
# siempre dice 'native'.
@app.route('/api/grafo/estado')
def grafo_estado():
    return jsonify({'store': 'native'})


# ── Voz de Khipu → core/voice_api.py (G5-05, lote I4) ──────────────────────────────────────────────────────────
# /api/voice/* (diagnóstico, voces, adoptar, ajuste fino, sincronizar, prompt, sesión firmada, audio del recorrido),
# BIXBY_SYSTEM_PROMPT y el contrato de herramientas viven allí. La config (ELEVENLABS_*) sigue aquí y el módulo la
# lee en cada llamada. Se re-exportan los nombres que leen el 🩺 (/api/diagnostics) y las pruebas.
import sys as _sys  # noqa: E402
from core import voice_api as _voice_api  # noqa: E402
from core.voice_api import (BIXBY_SYSTEM_PROMPT, RETIRED_VOICE_TOOLS, VOICE_COMPANY_VIEWS,  # noqa: E402,F401
                            VOICE_SCREEN_ALIASES, VOICE_SCREENS, VOICE_SIM_PRESETS, VOICE_TOUR_ACTIONS,
                            VOICE_UI_ACTIONS, _TOUR_AUDIO, _VOICE_TOOL_TIMEOUTS, _bixby_client_tools,
                            _sync_bixby_agent, voice_agent_diag)
_voice_api.bind(_sys.modules[__name__])
app.register_blueprint(_voice_api.voice_bp)
_voice_api.start_autosync()


# ══ CAPA 4 — INVESTIGACIÓN PROFUNDA (arquitectura de 4 capas, 2026-07-10) ═══
# Capa 1 (refleja): KHIPU parser + proxies + client tools de Khipu.
# Capa 2 (preconsciente): caché + core/semantic.py (subgrafo hiper-filtrado).
# Capa 3 (consciente): _ai_complete con SOLO el contexto relevante.
# Capa 4 (esta): bucle multi-paso para preguntas complejas — planear → reunir
# (capa 2) → simular (matrices) → sintetizar. Corre en background (30-90s);
# el cliente hace polling a /api/deep/status. Ver docs/ARQUITECTURA_CAPAS.md.
_deep_state = {'running': False, 'steps': [], 'result': None,
               'question': None, 'started_at': 0.0}


def _deep_run(question, company_ids):
    from core.semantic import build_context, extract_companies
    steps = _deep_state['steps']

    def step(nombre, detalle=''):
        steps.append({'paso': nombre, 'detalle': detalle})

    try:
        # 1) PLAN (consciente, barato)
        step('plan', 'Descomponiendo la pregunta en sub-análisis…')
        plan = []
        try:
            ptxt, _m = _ai_complete(
                'Eres un analista jefe. Responde SOLO un JSON: {"subpreguntas": ["...", "..."]} '
                '(2-3 sub-análisis concretos y verificables).',
                f'Pregunta del inversor: {question}', max_tokens=250)
            plan = (_extract_json(ptxt) or {}).get('subpreguntas') or []
        except Exception:  # noqa: BLE001
            pass
        if plan:
            step('plan_listo', ' · '.join(str(p)[:80] for p in plan[:3]))

        # 2) REUNIR — capa preconsciente: subgrafo hiper-filtrado
        ids = company_ids or extract_companies(question)
        ctx = build_context(ids, question)
        focos = [f['empresa'].get('label') or f['empresa'].get('id') for f in ctx['foco']]
        step('contexto', f'Subgrafo activo: {", ".join(focos) if focos else "global"} '
                         f'({ctx["universo"]["empresas"]} empresas en el universo)')

        # 3) SIMULAR — matrices del servidor (si hay DB); evidencia numérica real
        sim = None
        try:
            from ontology.db import ontology_available, session_scope
            if ontology_available() and ids:
                from matrix.engine import build_matrices, propagate, active_factors, fragility
                with session_scope() as s:
                    mats, idx, all_ids = build_matrices(s)
                    factors = active_factors(s)
                    frag = fragility(idx, factors)
                    shock = [i for i in ids if i in idx][:1]
                    if shock:
                        impacts, cascade = propagate(mats, idx, all_ids, shock, frag=frag)
                        top = sorted(((k, v) for k, v in impacts.items() if k not in shock),
                                     key=lambda kv: -kv[1])[:8]
                        sim = {'shock': shock[0], 'afectadas': max(len(impacts) - 1, 0),
                               'top_impactadas': [{'id': k, 'pct': round(v, 1)} for k, v in top],
                               'factores_activos': [f['label'] for f in factors]}
                        step('simulación', f'Si cae {shock[0]}: {sim["afectadas"]} empresas '
                                           f'afectadas; peor golpe {top[0][0] if top else "—"}')
        except Exception:  # noqa: BLE001
            step('simulación', 'Motor de matrices no disponible — análisis sin propagación numérica')

        # 4) SINTETIZAR — capa consciente con TODA la evidencia
        step('síntesis', 'Redactando el análisis final…')
        evidencia = json.dumps({'contexto': ctx, 'simulacion': sim, 'plan': plan},
                               ensure_ascii=False)[:14000]
        # Síntesis final = lo que importa → tier 'deep' (Sonnet 5) con más presupuesto.
        # (El PLAN del paso 1 queda 'fast': es barato y no necesita profundidad.)
        final, model = _ai_complete(
            'Eres el analista jefe de Khipus Finance Intelligence. Escribe en español, '
            'para un inversor exigente: 1) TESIS en 2-3 frases; 2) EVIDENCIA con los números '
            'del contexto/simulación (cita empresas y porcentajes REALES del JSON, jamás '
            'inventes); 3) RIESGOS (2-3 bullets); 4) QUÉ VIGILAR (2-3 señales concretas). '
            'Máximo ~350 palabras. Cierra con: "Análisis, no asesoría financiera."',
            f'Pregunta: {question}\n\nEVIDENCIA (JSON):\n{evidencia}',
            max_tokens=2400, tier='deep')
        _deep_state['result'] = {'answer': final, 'model': model, 'plan': plan,
                                 'sim': sim, 'focos': focos}
        step('listo', 'Análisis completo')
    except Exception as e:  # noqa: BLE001
        _deep_state['result'] = {'error': str(e)[:300]}
        step('error', str(e)[:120])
    finally:
        _deep_state['running'] = False


@app.route('/api/deep/analyze', methods=['POST'])
@rate_limit(limit=20, window=3600)
def deep_analyze():
    """Arranca una investigación profunda (Capa 4). Una a la vez por worker."""
    if not _ai_configured():
        return jsonify({'error': 'no AI provider configured'}), 400
    body = request.get_json(force=True, silent=True) or {}
    question = str(body.get('question', ''))[:600].strip()
    if not question:
        return jsonify({'error': 'question is required'}), 400
    if _deep_state['running']:
        return jsonify({'status': 'busy', 'question': _deep_state['question']}), 409
    from core.semantic import resolve_ids
    ids = resolve_ids(body.get('companies') or [])
    _deep_state.update(running=True, steps=[], result=None,
                       question=question, started_at=time.time())
    threading.Thread(target=_deep_run, args=(question, ids), daemon=True).start()
    return jsonify({'status': 'started', 'question': question})


# ── Diagnóstico remoto de clientes (para depurar "no pasa nada" sin ver la
# pantalla del usuario): el navegador envía beacons (GPU, WebGL, errores del
# 3D) a un buffer en memoria que se puede leer desde /api/diag/recent. Sin
# datos personales: solo user-agent, GPU y el error técnico. ──
_DIAGS = []


def _diag_persist(entry):
    """Persistir en Postgres si está disponible — el buffer en memoria se
    borra con CADA deploy y perdíamos los reportes del usuario (pasó 3 veces)."""
    try:
        from ontology.db import ontology_available, _get_engine
        if not ontology_available():
            return
        from sqlalchemy import text as _sqltext
        eng = _get_engine()
        with eng.begin() as c:
            c.execute(_sqltext(
                'CREATE TABLE IF NOT EXISTS client_diags '
                '(id SERIAL PRIMARY KEY, ts TIMESTAMPTZ DEFAULT now(), '
                'kind TEXT, ver TEXT, ua TEXT, data TEXT)'))
            c.execute(_sqltext(
                'INSERT INTO client_diags (kind, ver, ua, data) VALUES (:k, :v, :u, :d)'),
                {'k': entry['kind'], 'v': entry['ver'], 'u': entry['ua'],
                 'd': json.dumps(entry['data'], ensure_ascii=False)})
    except Exception:  # noqa: BLE001 — el diagnóstico jamás rompe nada
        pass


@app.route('/api/diag', methods=['POST'])
@rate_limit(limit=30, window=300)
def client_diag():
    b = request.get_json(silent=True) or {}
    entry = {
        'ts': datetime.now().isoformat(timespec='seconds'),
        'kind': str(b.get('kind', ''))[:40],
        'ver': str(b.get('ver', ''))[:20],
        'ua': str(b.get('ua', ''))[:160],
        'data': {k: str(v)[:200] for k, v in (b.get('data') or {}).items()} if isinstance(b.get('data'), dict) else {},
    }
    _DIAGS.append(entry)
    del _DIAGS[:-80]
    log.warning('DIAG %s %s %s', entry['kind'], entry['data'], entry['ua'][:60])
    _diag_persist(entry)
    return jsonify({'ok': True})


@app.route('/api/diag/recent')
@rate_limit(limit=30, window=3600)
@_require_operator
def client_diag_recent():
    # navegador + versión de quienes usan la app: solo para el operador (limpieza 2026-10-11: era pública)
    rows = []
    try:
        from ontology.db import ontology_available, _get_engine
        if ontology_available():
            from sqlalchemy import text as _sqltext
            eng = _get_engine()
            with eng.connect() as c:
                rs = c.execute(_sqltext(
                    'SELECT ts, kind, ver, ua, data FROM client_diags ORDER BY id DESC LIMIT 50'))
                for r in rs:
                    rows.append({'ts': str(r[0])[:19], 'kind': r[1], 'ver': r[2],
                                 'ua': r[3], 'data': json.loads(r[4] or '{}')})
    except Exception:  # noqa: BLE001
        pass
    combined = rows if rows else _DIAGS[-50:]
    return jsonify({'count': len(combined), 'diags': combined, 'persistent': bool(rows)})


@app.route('/api/deep/status')
def deep_status():
    return jsonify({'running': _deep_state['running'], 'question': _deep_state['question'],
                    'steps': _deep_state['steps'], 'result': _deep_state['result'],
                    'seconds': int(time.time() - _deep_state['started_at']) if _deep_state['started_at'] else 0})

def _portfolio_risk_impl(positions, no_data_msg):
    """Cálculo VaR/CVaR/Sharpe/MaxDD compartido por /api/portfolio-risk (interno)
    y /v1/risk/portfolio (API pública JWT — contrato INTOCABLE, antes era un
    duplicado verbatim de ~60 líneas). Devuelve (payload_dict, status)."""
    try:
        import numpy as np
    except Exception:  # noqa: BLE001
        return {'error': 'numpy not installed on server'}, 503

    returns_by_ticker = {}
    for ticker in list(positions.keys())[:10]:
        try:
            r, _ = _safe_get(
                f'https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY_ADJUSTED'
                f'&symbol={ticker}&apikey={AV_KEY}', timeout=10)
            ts = (r or {}).get('Weekly Adjusted Time Series', {})
            prices = [float(v['5. adjusted close']) for k, v in sorted(ts.items(), reverse=True)][:52]
            if len(prices) > 4:
                returns_by_ticker[ticker] = [(prices[i] - prices[i + 1]) / prices[i + 1]
                                             for i in range(len(prices) - 1)]
        except Exception:  # noqa: BLE001
            pass
    if not returns_by_ticker:
        return {'error': no_data_msg}, 400

    pv = sum(p['shares'] * p['buy_price'] for p in positions.values())
    portfolio_returns = []
    for ticker, pos in positions.items():
        if ticker not in returns_by_ticker:
            continue
        weight = (pos['shares'] * pos['buy_price']) / pv
        portfolio_returns.append([x * weight for x in returns_by_ticker[ticker]])
    if not portfolio_returns:
        return {'error': 'Insufficient data'}, 400

    min_len = min(len(r) for r in portfolio_returns)
    combined = np.sum([r[:min_len] for r in portfolio_returns], axis=0)
    mu, sigma = float(np.mean(combined)), float(np.std(combined))
    var_1w = abs((mu - 1.645 * sigma) * pv)
    var_1m = var_1w * np.sqrt(4)
    cvar = abs(float(np.mean(combined[combined <= np.percentile(combined, 5)])) * pv)
    sharpe = float((mu / sigma) * np.sqrt(52)) if sigma else 0
    cum = np.cumprod(1 + combined)
    peak = np.maximum.accumulate(cum)
    mdd = float(abs(np.min((cum - peak) / peak)))

    return {
        'portfolio_value': round(pv, 2),
        'var_95': {'weekly_usd': round(var_1w, 2), 'monthly_usd': round(var_1m, 2),
                   'pct': round(var_1w / pv * 100, 2)},
        'cvar_95': {'usd': round(cvar, 2), 'pct': round(cvar / pv * 100, 2)},
        'sharpe_ratio': round(sharpe, 3),
        'max_drawdown_pct': round(mdd * 100, 2),
        'risk_level': 'BAJO' if var_1w / pv < 0.03 else 'MODERADO' if var_1w / pv < 0.06 else 'ALTO',
    }, 200


@app.route('/api/portfolio/risk_report', methods=['POST'])
@rate_limit(limit=20, window=3600)
def portfolio_risk_report():
    """REPORTE DE RIESGO (VaR/CVaR/volatilidad/beta/correlaciones/contribución)
    con precios diarios REALES de 1 año. Body: {positions:[{symbol, shares,
    label?}], horizon_days?}. No toca /api/portfolio-risk ni /v1 (contratos)."""
    from core.risk_report import build_report
    body = request.get_json(silent=True) or {}
    pos = body.get('positions')
    if not isinstance(pos, list) or not pos:
        return jsonify({'ok': False, 'error': 'positions requerido: [{symbol, shares} o {symbol, usd}]'}), 400
    try:
        horizon = min(max(int(body.get('horizon_days') or 10), 1), 30)
    except (TypeError, ValueError):
        horizon = 10
    try:
        return jsonify(build_report(pos, horizon=horizon))
    except Exception as e:  # noqa: BLE001
        log.warning('risk_report: %s', e)
        return jsonify({'ok': False, 'error': 'error interno al calcular el reporte'}), 500


@app.route('/api/portfolio/vega_report', methods=['POST'])
@rate_limit(limit=30, window=3600)
def portfolio_vega_report():
    """REPORTE VEGA (Kappa) de opciones: griegas Black-Scholes con volatilidad
    implícita EN VIVO del contrato. Body: {options:[{symbol, kind, strike,
    expiry, contracts}]} (contracts < 0 = posición corta)."""
    from core.options import vega_report
    body = request.get_json(silent=True) or {}
    opts = body.get('options')
    if not isinstance(opts, list) or not opts:
        return jsonify({'ok': False, 'error': 'options requerido: [{symbol, kind, strike, expiry, contracts}]'}), 400
    try:
        return jsonify(vega_report(opts))
    except Exception as e:  # noqa: BLE001
        log.warning('vega_report: %s', e)
        return jsonify({'ok': False, 'error': 'error interno al valorar las opciones'}), 500


@app.route('/api/options/chain/<symbol>')
@rate_limit(limit=120, window=3600)
def options_chain(symbol):
    """Vencimientos y strikes disponibles del subyacente (selectores de la UI)."""
    from core.options import chain_meta
    safe = _safe_ticker(symbol)
    if not safe:
        return jsonify({'available': False, 'error': 'ticker inválido'}), 400
    exp = request.args.get('expiry')
    return jsonify(chain_meta(safe, exp if exp and re.fullmatch(r'\d{4}-\d{2}-\d{2}', exp) else None))


@app.route('/api/portfolio-risk', methods=['POST'])
@rate_limit(limit=20, window=3600)
def api_portfolio_risk_internal():
    """VaR + CVaR del portfolio — endpoint interno sin JWT (para uso del browser)."""
    data = request.get_json(silent=True) or {}
    positions = data.get('positions', {})
    if not positions:
        return jsonify({'error': 'positions required',
                        'format': '{"NVDA":{"shares":10,"buy_price":450}}'}), 400
    if not AV_KEY:
        return jsonify({'error': 'AV_KEY not configured on server. Add ALPHA_VANTAGE_KEY to .env'}), 400
    payload, status = _portfolio_risk_impl(
        positions, 'Could not fetch historical data. Check AV_KEY on server.')
    return jsonify(payload), status


# ════════════════════════════════════════════════════════════════════════════
# API PÚBLICA v1 — autenticación JWT por tiers (modelo de negocio)
# ════════════════════════════════════════════════════════════════════════════
TIER_DAY_LIMITS = {'free': 100, 'starter': 5000, 'pro': 25000, 'business': 100000, 'enterprise': None}


def generate_khipu_key(user_id, tier='starter'):
    payload = {'sub': user_id, 'tier': tier, 'iat': datetime.utcnow(), 'jti': str(uuid.uuid4())}
    return 'kfi_' + jwt.encode(payload, SECRET_KEY, algorithm='HS256')


def validate_khipu_key(key):
    if not key or not key.startswith('kfi_'):
        return None, 'Invalid key format'
    try:
        return jwt.decode(key[4:], SECRET_KEY, algorithms=['HS256']), None
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def khipu_auth(min_tier='free'):
    order = list(TIER_DAY_LIMITS.keys())

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not _HAS_JWT:
                return jsonify({'error': 'Public API disabled (PyJWT not installed)'}), 503
            key = request.headers.get('X-KHIPU-Key') or request.args.get('api_key')
            payload, err = validate_khipu_key(key)
            if err:
                return jsonify({'error': err, 'docs': '/docs'}), 401
            tier = payload.get('tier', 'free')
            if order.index(tier) < order.index(min_tier):
                return jsonify({'error': f'Requires {min_tier} tier', 'upgrade': '/pricing'}), 403
            request.khipu_user = payload
            return f(*args, **kwargs)
        return wrapper
    return decorator


@app.route('/v1/auth/key', methods=['POST'])
def api_issue_key():
    """Issue a Khipu Finance API key. Body: {user_id, tier}. Tiers: free/starter/pro/business/enterprise."""
    if not _HAS_JWT:
        return jsonify({'error': 'PyJWT not installed — JWT API disabled'}), 503
    body = request.get_json(silent=True) or {}
    user_id = body.get('user_id') or body.get('email') or str(uuid.uuid4())
    tier = body.get('tier', 'free')
    if tier not in TIER_DAY_LIMITS:
        return jsonify({'error': f'Unknown tier. Valid: {list(TIER_DAY_LIMITS.keys())}'}), 400
    # Solo el tier 'free' es de autoservicio; los de pago exigen la credencial
    # de administrador (antes cualquiera podía emitirse una clave enterprise)
    if tier != 'free':
        admin = request.headers.get('X-Admin-Secret', '')
        if not KHIPU_ADMIN_SECRET or not hmac.compare_digest(admin, KHIPU_ADMIN_SECRET):
            return jsonify({'error': 'Paid tiers require admin credential (X-Admin-Secret)'}), 403
    key = generate_khipu_key(user_id, tier)
    return jsonify({'api_key': key, 'tier': tier, 'user_id': user_id, 'note': 'Pass as X-KHIPU-Key header or ?api_key= query param'})


@app.route('/docs', methods=['GET'])
def api_docs():
    return jsonify({
        'name': 'Khipu Finance API v1',
        'version': '1.0.0',
        'endpoints': {
            'POST /v1/auth/key': 'Issue API key (body: {user_id, tier})',
            'POST /api/portfolio-risk': 'VaR/CVaR/Sharpe for portfolio (no auth, internal)',
            'GET  /v1/nodes': 'Node universe metadata [free]',
            'GET  /v1/nodes/<id>/live': 'Live quote + fundamentals for a node [starter]',
            'POST /v1/risk/portfolio': 'VaR/CVaR/Sharpe for portfolio [starter]',
            'GET  /api/space/launches': 'Upcoming space launches (Launch Library 2)',
            'GET  /api/news/gdelt/<company>': 'Global news via GDELT',
            'GET  /api/voice/session': 'Khipu ElevenLabs signed session URL',
            'GET  /api/health': 'Service health check',
        },
        'tiers': list(TIER_DAY_LIMITS.keys()),
        'auth': 'X-KHIPU-Key header or ?api_key= param',
    })


@app.route('/v1/nodes', methods=['GET'])
@khipu_auth('free')
def api_nodes():
    return jsonify({'count': 450, 'note': 'Full node data in the JS bundle. Use /v1/nodes/{id}/live for details.'})


@app.route('/v1/nodes/<node_id>/live', methods=['GET'])
@khipu_auth('starter')
def api_node_live(node_id):
    ticker = _safe_ticker(request.args.get('ticker'))
    quote = {}
    if ticker and FINNHUB:
        q, _ = _fetch_quote_raw(ticker)
        if q and q.get('c'):
            quote = {'price': q['c'], 'prev_close': q['pc'],
                     'change_pct': (q['c'] - q['pc']) / q['pc'] * 100 if q['pc'] else 0}
    return jsonify({'node_id': node_id, 'quote': quote, 'status': 'live' if quote else 'no_data'})


@app.route('/v1/risk/portfolio', methods=['POST'])
@khipu_auth('starter')
def api_portfolio_risk():
    """VaR + CVaR del portfolio del cliente (Alpha Vantage históricos).
    Contrato público INTOCABLE — mismo cálculo compartido en _portfolio_risk_impl."""
    data = request.get_json(silent=True) or {}
    positions = data.get('positions', {})
    if not positions:
        return jsonify({'error': 'positions required',
                        'format': '{"NVDA":{"shares":10,"buy_price":450}}'}), 400
    payload, status = _portfolio_risk_impl(
        positions, 'Could not fetch historical data. Check ALPHA_VANTAGE_KEY.')
    return jsonify(payload), status


# ── /api/quotes/live — lote EN VIVO (Finnhub→Yahoo, paralelo, caché 15 s) ──
@app.route('/api/quotes/live', methods=['POST'])
@rate_limit(limit=60, window=60)
def quotes_live():
    """Lote de cotizaciones en vivo. Body: {"tickers": ["NVDA","TSM","7203.T",…]}
    (máx 150 por petición; el cliente recorre TODO el catálogo en lotes).
    Respuesta: {quotes: {T: {close, prev, pct, live:<número>, provider, as_of,
    age_seconds, currency, converted, vol, market_state}}, n, cached, as_of,
    providers, finnhub_quota}. Cascada core/providers (Finnhub→Yahoo para TODO
    ticker), 8 hilos en paralelo, caché 15 s (core.quotes.fetch_quotes_live).
    Un ticker sin dato no aparece: nunca se inventa un precio."""
    data = request.get_json(silent=True) or {}
    tickers = [s for s in (_safe_ticker(t) for t in (data.get('tickers') or [])) if s]
    if not tickers:
        return jsonify({'error': 'tickers required / faltan tickers'}), 400
    from core.quotes import LIVE_MAX_TICKERS, fetch_quotes_live
    truncated = len(tickers) > LIVE_MAX_TICKERS
    try:
        res = fetch_quotes_live(tickers[:LIVE_MAX_TICKERS])
    except Exception as e:  # noqa: BLE001
        log.warning('quotes_live: %s', type(e).__name__)
        return jsonify({'error': 'error interno al consultar las fuentes / internal error',
                        'quotes': {}, 'n': 0}), 503
    res['requested'] = len(tickers)
    res['max_per_request'] = LIVE_MAX_TICKERS
    if truncated:
        res['truncated'] = True
    res['finnhub_configured'] = bool(FINNHUB)
    return jsonify(res)


# ── /api/macro/fred — FRED macro indicators ───────────────────────────────────
@app.route('/api/macro/fred')
@rate_limit(limit=60, window=60)
@cache.cached(timeout=3600, query_string=True)
def macro_fred():
    """Fetch FRED series (free, no key). ?series=DXY,T10Y2Y,FEDFUNDS
    Returns last 30 data points per series.
    """
    import csv as _csv
    import io as _io

    series_param = request.args.get('series', 'T10Y2Y,FEDFUNDS,DGS10')
    series_ids = [s.strip() for s in series_param.split(',')
                  if s.strip() and re.match(r'^[A-Za-z0-9]{1,20}$', s.strip())][:8]
    out = {}
    for sid in series_ids:
        try:
            r = requests.get(
                f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}',
                headers={'User-Agent': 'Mozilla/5.0 (compatible; Khipu/1.0)'},
                timeout=10)
            if r.status_code == 200 and r.text:
                rows = list(_csv.reader(_io.StringIO(r.text)))
                data_rows = [(row[0], row[1]) for row in rows[1:]
                             if len(row) >= 2 and row[1] not in ('.', '')]
                data_rows = data_rows[-30:]
                out[sid] = [{'date': d, 'value': float(v)} for d, v in data_rows]
        except Exception:  # noqa: BLE001
            out[sid] = []
    resp = jsonify(out)
    return _degraded(resp) if any(not out.get(sid) for sid in series_ids) else resp


# ── /api/investors/13f/<ticker> — SEC 13F institutional holders ───────────────
_13f_cache: dict = {}


@app.route('/api/investors/13f/<ticker>')
@rate_limit(limit=60, window=60)
def investors_13f(ticker):
    """Top institutional holders from SEC EDGAR 13F filings. Cached 24h."""
    ticker = _safe_ticker(ticker)
    if not ticker:
        return jsonify({'error': 'invalid ticker'}), 400
    cached = _13f_cache.get(ticker)
    if cached and time.time() - cached['ts'] < 86400:
        return jsonify(cached['data'])

    today = datetime.utcnow().date()
    start = today - timedelta(days=90)
    from urllib.parse import quote as _urlquote
    url = (
        f'https://efts.sec.gov/LATEST/search-index?q=%22{_urlquote(ticker)}%22'
        f'&dateRange=custom&startdt={start.isoformat()}&enddt={today.isoformat()}&forms=13F-HR'
    )
    try:
        r = requests.get(url,
                         headers={'User-Agent': 'Khipu Finance research@khipu.finance',
                                  'Accept': 'application/json'},
                         timeout=12)
        if r.status_code != 200:
            return jsonify({'error': f'SEC returned {r.status_code}'}), 502
        data = r.json()
        hits = (data.get('hits') or {}).get('hits', [])
        holders = []
        seen = set()
        for h in hits[:20]:
            src = h.get('_source', {})
            disp = src.get('display_names', [])
            filer = src.get('entity_name') or (disp[0] if disp else None)
            if not filer or filer in seen:
                continue
            seen.add(filer)
            holders.append({
                'name': filer,
                'filed': src.get('period_of_report') or src.get('file_date'),
                'form': src.get('form_type', '13F-HR'),
                'cik': src.get('entity_id'),
            })
            if len(holders) >= 10:
                break
        result = {'ticker': ticker, 'holders': holders, 'source': 'SEC EDGAR'}
        _13f_cache[ticker] = {'ts': time.time(), 'data': result}
        return jsonify(result)
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200]}), 502


# ── /api/supply-chain/trade-flows — UN Comtrade bilateral trade data ──────────
@app.route('/api/supply-chain/trade-flows')
@rate_limit(limit=60, window=60)
@cache.cached(timeout=86400, query_string=True)
def trade_flows():
    """UN Comtrade public preview API — bilateral semiconductor trade.
    ?reporter=USA&partner=CHN&product=8542 (optional filters)
    HS codes: 8541 semiconductors, 8542 ICs, 8471 computers, 8473 computer parts
    """
    reporter = request.args.get('reporter', 'USA')
    partner  = request.args.get('partner', 'CHN')
    product  = request.args.get('product', '')
    if product and not re.match(r'^\d{2,6}$', product):
        product = ''

    _ISO_NUM = {
        'USA': '842', 'CHN': '156', 'TWN': '490', 'KOR': '410',
        'JPN': '392', 'DEU': '276', 'GBR': '826', 'NLD': '528',
        'SGP': '702', 'IND': '356', 'MEX': '484', 'MYS': '458',
    }
    reporter_code = _ISO_NUM.get(reporter.upper(), re.sub(r'[^A-Za-z0-9]', '', reporter)[:6])
    partner_code  = _ISO_NUM.get(partner.upper(), re.sub(r'[^A-Za-z0-9]', '', partner)[:6])

    hs_codes = [product] if product else ['8541', '8542', '8471', '8473']
    combined = []
    failed = 0
    for hs in hs_codes:
        url = (
            f'https://comtradeapi.un.org/public/v1/preview/C/A/HS'
            f'?reporterCode={reporter_code}&partnerCode={partner_code}'
            f'&cmdCode={hs}&period=2023'
        )
        try:
            r = requests.get(url,
                             headers={'User-Agent': 'Mozilla/5.0 (compatible; Khipu/1.0)'},
                             timeout=15)
            if r.status_code == 200:
                j = r.json()
                for item in (j.get('data') or [])[:5]:
                    combined.append({
                        'hs_code': hs,
                        'reporter': item.get('reporterDesc', reporter),
                        'partner': item.get('partnerDesc', partner),
                        'flow': item.get('flowDesc', ''),
                        'value_usd': item.get('primaryValue'),
                        'quantity': item.get('netWgt'),
                        'year': item.get('period'),
                    })
            else:
                failed += 1
        except Exception:  # noqa: BLE001
            failed += 1

    resp = jsonify({
        'reporter': reporter,
        'partner': partner,
        'hs_codes': hs_codes,
        'flows': combined,
        'source': 'UN Comtrade public preview',
    })
    return _degraded(resp) if failed else resp


# ── AI Trading Agent → core/trading_agent.py (G5-05, lote I4) ─────────────────────────────────────────────────
# /api/trade/agent/* y el ciclo del agente viven allí; usa la config y los ayudantes de la casa de aquí (bind).
import sys as _sys  # noqa: E402
from core import trading_agent as _trading_agent  # noqa: E402
from core.trading_agent import (_AGENT, _AGENT_RESTORE, _TRADABLE_CACHE, _AgentOrderError,  # noqa: E402,F401
                                _agent_order, _agent_run_cycle, _agent_universe)
_trading_agent.bind(_sys.modules[__name__])
app.register_blueprint(_trading_agent.trading_agent_bp)


@app.route('/api/trade/history', methods=['GET'])
@rate_limit(limit=60, window=60)
@_trade_auth
def trade_history():
    if not ALPACA_KEY:
        return jsonify([])
    try:
        r = requests.get(f'{ALPACA_BASE}/v2/orders?status=all&limit=50&direction=desc',
                         headers=_alpaca_hdrs(), timeout=10)
        return jsonify(r.json()), r.status_code
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200]}), 502


@app.route('/api/portfolio/comment', methods=['POST'])
@rate_limit(limit=40, window=3600)
def portfolio_comment():
    """Comentario CAUTO de Khipu sobre el portafolio (papel). Recibe un resumen
    AGREGADO y anónimo desde el cliente (sin datos personales: solo símbolos
    públicos + porcentajes) y devuelve 1-2 frases prudentes: observa concentración
    / diversificación, NUNCA una orden de compra/venta ni promesa de rendimiento.
    Si la IA falla, devuelve un comentario determinista de respaldo (nunca 500)."""
    body = request.get_json(force=True, silent=True) or {}
    lang = 'en' if str(body.get('lang', 'es')).lower().startswith('en') else 'es'
    try:
        equity = round(float(body.get('equity') or 0))
    except (TypeError, ValueError):
        equity = 0
    pnl_pct = body.get('pnl_pct')
    paper = body.get('paper')
    is_paper = paper is not False   # None/True → papel (default SEGURO); solo False explícito = dinero real
    n_pos = int(body.get('positions_count') or 0)
    sectors = body.get('sectors') or []      # [{sector, pct}]
    best = body.get('best') or {}
    worst = body.get('worst') or {}
    top = sectors[0] if sectors else None
    top_pct = 0
    try:
        top_pct = float(top.get('pct') or 0) if top else 0
    except (TypeError, ValueError):
        top_pct = 0

    # Respaldo determinista (sin IA) — cauto y honesto.
    if lang == 'en':
        fb = 'Simulated portfolio. ' if is_paper else 'Real-money portfolio. '
        if top and top_pct >= 50:
            fb += f"It leans heavily on {top.get('sector')} (~{round(top_pct)}%); some diversification would lower single-sector risk. "
        elif n_pos <= 1:
            fb += 'With a single position the whole outcome rides on one name; spreading across a few would reduce risk. '
        else:
            fb += 'Reasonably spread — keep an eye on concentration and news on your largest holdings. '
        fb += ('This is an observation on paper money, not financial advice.' if is_paper
               else 'This is an observation on a real-money account, not financial advice.')
    else:
        fb = 'Portafolio simulado. ' if is_paper else 'Portafolio con DINERO REAL. '
        if top and top_pct >= 50:
            fb += f"Está muy cargado en {top.get('sector')} (~{round(top_pct)}%); algo de diversificación reduciría el riesgo de un solo sector. "
        elif n_pos <= 1:
            fb += 'Con una sola posición, todo depende de un nombre; repartir en varios reduciría el riesgo. '
        else:
            fb += 'Razonablemente repartido — vigila la concentración y las noticias de tus mayores posiciones. '
        fb += ('Es una observación sobre dinero de papel, no asesoría financiera.' if is_paper
               else 'Es una observación sobre una cuenta de dinero real, no asesoría financiera.')

    if not _ai_configured():
        return jsonify({'ok': True, 'comment': fb, 'model': 'fallback'})

    lang_name = 'inglés' if lang == 'en' else 'español'
    money_ctx = 'dinero de PAPEL (simulado)' if is_paper else 'DINERO REAL'
    money_close = ('es dinero de papel y no es asesoría financiera' if is_paper
                   else 'es una cuenta de DINERO REAL y esto no es asesoría financiera')
    system = (
        'Eres Khipu, un observador financiero PRUDENTE dentro de una app con '
        + money_ctx + '. Comentas un portafolio en 1-2 frases, en ' + lang_name + '. '
        'REGLAS INNEGOCIABLES: (1) NUNCA des una orden ni recomendación directa de comprar o '
        'vender un activo concreto. (2) Puedes observar concentración, diversificación y riesgo '
        'en términos generales. (3) NUNCA prometas rendimientos ni uses lenguaje de certeza. '
        '(4) Cierra recordando que ' + money_close + '. '
        'Tono cálido, claro y breve. Devuelve SOLO el comentario, sin viñetas ni JSON.'
    )
    secs = ', '.join(f"{s.get('sector')} {round(float(s.get('pct') or 0))}%" for s in sectors[:4]) or '—'
    prompt = (
        f"Portafolio simulado. Valor total ~${equity}. Rendimiento total {pnl_pct}%. "
        f"Posiciones abiertas: {n_pos}. Concentración por sector: {secs}. "
        f"Mejor posición: {best.get('symbol', '—')} {best.get('pnl_pct', '')}%. "
        f"Peor posición: {worst.get('symbol', '—')} {worst.get('pnl_pct', '')}%. "
        "Da tu observación prudente."
    )
    try:
        text, model = _ai_complete(system, prompt, max_tokens=350, tier='fast')
        text = (text or '').strip()
        if not text:
            return jsonify({'ok': True, 'comment': fb, 'model': 'fallback'})
        return jsonify({'ok': True, 'comment': text, 'model': model})
    except Exception as e:  # noqa: BLE001
        return jsonify({'ok': True, 'comment': fb, 'model': 'fallback', 'error': str(e)[:120]})


@app.route('/api/portfolio/advice', methods=['POST'])
@rate_limit(limit=30, window=3600)
def portfolio_advice():
    """CAPA PROACTIVA (elección de Fabrizio: 'sugiere y tú decides'). Dado un
    resumen ANÓNIMO de la cartera (papel) + candidatos del universo, Khipu razona
    con Opus 4.8 (el mejor juicio para esto) y devuelve un pulso + 1-3 sugerencias
    CONCRETAS (incluir/reducir/vigilar), cada una con su porqué. NUNCA ejecuta nada
    — el cliente pide aprobación por acción. Respaldo determinista si la IA falla."""
    body = request.get_json(force=True, silent=True) or {}
    lang = 'en' if str(body.get('lang', 'es')).lower().startswith('en') else 'es'
    is_paper = body.get('paper') is not False
    equity = body.get('equity')
    pnl_pct = body.get('pnl_pct')
    positions = body.get('positions') or []       # [{symbol, sector, pct, pnl_pct}]
    sectors = body.get('sectors') or []           # [{sector, pct}]
    candidates = body.get('candidates') or []     # [{label, ticker, sector, nrs}]

    try:
        eq_txt = '$' + format(int(round(float(equity or 0))), ',')
    except (TypeError, ValueError):
        eq_txt = '$0'
    top = sectors[0] if sectors else None
    if lang == 'en':
        pulse_fb = f"Portfolio at {eq_txt}, {'+' if (pnl_pct or 0) >= 0 else ''}{pnl_pct}% overall. This is an observation, not financial advice."
    else:
        pulse_fb = f"Cartera en {eq_txt}, {'+' if (pnl_pct or 0) >= 0 else ''}{pnl_pct}% en total. Es una observación, no asesoría financiera."
    sugg_fb = []
    try:
        if top and float(top.get('pct') or 0) >= 50:
            sugg_fb.append({'action': 'reduce', 'target': top.get('sector'),
                            'rationale': (f"~{round(float(top.get('pct')))}% en {top.get('sector')}; reducir bajaría el riesgo de un solo sector."
                                          if lang == 'es' else
                                          f"~{round(float(top.get('pct')))}% in {top.get('sector')}; trimming would lower single-sector risk."),
                            'severity': 'media'})
    except (TypeError, ValueError):
        pass
    fallback = {'ok': True, 'pulse': pulse_fb, 'suggestions': sugg_fb, 'model': 'fallback'}

    if not _ai_configured():
        return jsonify(fallback)

    lang_name = 'inglés' if lang == 'en' else 'español'
    money = 'dinero de PAPEL (simulado)' if is_paper else 'DINERO REAL'
    system = (
        'Eres Khipu, asesor financiero PRUDENTE de una app con ' + money + '. Analizas una '
        'cartera y sugieres en ' + lang_name + '. REGLAS INNEGOCIABLES: (1) Propones acciones '
        'CONCRETAS (incluir/reducir/vigilar un nombre o sector) pero el usuario SIEMPRE aprueba; '
        'tú solo SUGIERES, nunca ordenas ni prometes rendimiento. (2) Basa todo en concentración, '
        'diversificación y riesgo, usando SOLO los datos dados (posiciones, sectores, candidatos). '
        'No inventes precios ni cifras. (3) Máximo 3 sugerencias, las más útiles; prioriza los '
        'candidatos dados para "add". (4) El pulso cierra recordando que es observación, no '
        'asesoría financiera. Devuelve SOLO JSON válido: '
        '{"pulse":"1 frase de cómo va la cartera","suggestions":[{"action":"add|reduce|watch",'
        '"target":"nombre o sector","ticker":"TICKER o vacío","rationale":"1 frase","severity":"baja|media|alta"}]}'
    )
    prompt = (
        'CARTERA (' + ('papel' if is_paper else 'real') + '): valor ~' + eq_txt + ', rendimiento ' + str(pnl_pct) + '%.\n'
        'POSICIONES: ' + json.dumps(positions[:20], ensure_ascii=False) + '\n'
        'CONCENTRACIÓN POR SECTOR: ' + json.dumps(sectors[:8], ensure_ascii=False) + '\n'
        'CANDIDATOS para incluir (del universo, NO en cartera): ' + json.dumps(candidates[:20], ensure_ascii=False) + '\n'
        'Da tu pulso y hasta 3 sugerencias.'
    )
    try:
        # Sonnet 5 (elección de Fabrizio por costo/velocidad): 90% del juicio de
        # Opus, 2-3x más rápido y ~mitad de costo. Se puede subir a claude-opus-4-8
        # por tarea si alguna lo amerita (cambiar solo este string).
        text, model = _ai_complete(system, prompt, max_tokens=900, model='claude-sonnet-5-5')
        data = _extract_json(text)
        if not isinstance(data, dict):
            return jsonify(fallback)
        sug = data.get('suggestions')
        return jsonify({'ok': True, 'pulse': (data.get('pulse') or pulse_fb),
                        'suggestions': (sug if isinstance(sug, list) else [])[:3], 'model': model})
    except Exception as e:  # noqa: BLE001
        fallback['error'] = str(e)[:120]
        return jsonify(fallback)


@app.route('/api/trade/positions/detail', methods=['GET'])
@rate_limit(limit=60, window=60)
@_trade_auth
def trade_positions_detail():
    if not ALPACA_KEY:
        return jsonify([])
    try:
        r = requests.get(f'{ALPACA_BASE}/v2/positions', headers=_alpaca_hdrs(), timeout=10)
        positions = r.json()
        if not isinstance(positions, list):
            return jsonify(positions), r.status_code
        enriched = []
        for p in positions:
            enriched.append({
                'symbol':      p.get('symbol'),
                'asset_class': p.get('asset_class', 'us_equity'),   # 'crypto' en posiciones cripto → sector correcto en el informe
                'qty':         float(p.get('qty') or 0),
                'side':        p.get('side', 'long'),
                'avg_entry':   float(p.get('avg_entry_price') or 0),
                'current':     float(p.get('current_price') or 0),
                'market_val':  float(p.get('market_value') or 0),
                'unrealized':  float(p.get('unrealized_pl') or 0),
                'unrealized_pct': float(p.get('unrealized_plpc') or 0) * 100,
                'cost_basis':  float(p.get('cost_basis') or 0),
            })
        return jsonify(enriched)
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200]}), 502


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5050))
    app.run(host='0.0.0.0', port=port, debug=False)
