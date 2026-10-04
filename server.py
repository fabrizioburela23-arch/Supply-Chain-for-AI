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
from flask import Flask, jsonify, send_file, request
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
load_dotenv()  # Lee .env: FINNHUB_KEY, FMP_KEY, CLAUDE_KEY, MARKETSTACK_KEY, AI_MODEL

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
                       ('core.portfolio_reports_api', 'portfolio_reports_bp'), ('core.decide_api', 'decide_bp')):
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

# ── Sala de Situación geopolítica (opcional) — /api/geo/* ────────────────────
try:
    from core.geosit import geo_bp
    app.register_blueprint(geo_bp)
except Exception as _e:  # noqa: BLE001
    log.warning('Sala de Situación no registrada (opcional): %s', _e)


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


# ── Voz de Khipu: diagnóstico y ajuste FINO del agente ElevenLabs ────────────
@app.route('/api/voice/agent-diag')
def voice_agent_diag():
    """QUÉ voz/modelo/idioma tiene el agente de ElevenLabs AHORA — para
    diagnosticar 'la voz rara' con datos, no a ciegas. Solo lectura."""
    if not (ELEVENLABS_KEY and ELEVENLABS_AGENT_ID):
        return jsonify({'ok': False, 'reason': 'ELEVENLABS_KEY/AGENT_ID no configurados'})
    try:
        r = requests.get(f'https://api.elevenlabs.io/v1/convai/agents/{ELEVENLABS_AGENT_ID}',
                         headers={'xi-api-key': ELEVENLABS_KEY}, timeout=10)
        if not r.ok:
            return jsonify({'ok': False, 'status': r.status_code, 'body': r.text[:180]})
        cfg = r.json() or {}
        conv = cfg.get('conversation_config') or {}
        tts = conv.get('tts') or {}
        agent = conv.get('agent') or {}
        voice_id = tts.get('voice_id')
        voice_name = None
        if voice_id:
            try:
                vr = requests.get(f'https://api.elevenlabs.io/v1/voices/{voice_id}',
                                  headers={'xi-api-key': ELEVENLABS_KEY}, timeout=8)
                if vr.ok:
                    voice_name = (vr.json() or {}).get('name')
            except Exception:  # noqa: BLE001
                pass
        return jsonify({'ok': True, 'name': cfg.get('name'),
                        'voice_id': voice_id, 'voice_name': voice_name,
                        'tts_model': tts.get('model_id'),
                        'language': agent.get('language'),
                        'llm': ((agent.get('prompt') or {}).get('llm')),
                        'first_message': (agent.get('first_message') or '')[:120]})
    except Exception as e:  # noqa: BLE001
        return jsonify({'ok': False, 'error': str(e)[:160]})


@app.route('/api/voice/voices')
def voice_voices():
    """Voces disponibles: las de la cuenta + las mejor valoradas EN ESPAÑOL de
    la biblioteca compartida de ElevenLabs (para arreglar la 'voz rara': el
    agente tenía una voz en inglés hablando español). Solo lectura."""
    if not ELEVENLABS_KEY:
        return jsonify({'error': 'ELEVENLABS_KEY no configurada'}), 400
    out = {'mine': [], 'shared_es': [], 'upstream': {}}
    try:
        r = requests.get('https://api.elevenlabs.io/v1/voices',
                         headers={'xi-api-key': ELEVENLABS_KEY}, timeout=10)
        out['upstream']['mine'] = r.status_code if not r.ok else 200
        if not r.ok:
            out['upstream']['mine_body'] = r.text[:160]
        if r.ok:
            for v in (r.json() or {}).get('voices', [])[:60]:
                out['mine'].append({'voice_id': v.get('voice_id'), 'name': v.get('name'),
                                    'category': v.get('category'),
                                    'labels': v.get('labels') or {}})
    except Exception as e:  # noqa: BLE001
        out['upstream']['mine_err'] = str(e)[:120]
    try:
        r = requests.get('https://api.elevenlabs.io/v1/shared-voices',
                         params={'language': 'es', 'page_size': 12},
                         headers={'xi-api-key': ELEVENLABS_KEY}, timeout=10)
        out['upstream']['shared'] = r.status_code if not r.ok else 200
        if not r.ok:
            out['upstream']['shared_body'] = r.text[:160]
        if r.ok:
            for v in (r.json() or {}).get('voices', [])[:12]:
                out['shared_es'].append({'voice_id': v.get('voice_id'),
                                         'public_owner_id': v.get('public_owner_id'),
                                         'name': v.get('name'),
                                         'gender': v.get('gender'), 'accent': v.get('accent'),
                                         'age': v.get('age'), 'use_case': v.get('use_case'),
                                         'usage_7d': v.get('usage_character_count_7d')})
    except Exception as e:  # noqa: BLE001
        out['upstream']['shared_err'] = str(e)[:120]
    return jsonify(out)


# Rutas que REESCRIBEN el agente de ElevenLabs (voz, modelo, idioma, prompt):
# además del candado ELEVENLABS_ALLOW_OVERRIDE exigen el PIN de operador
# (core.pin.require_operator, mismo contador anti-adivinanza que el trading).
# Sin TRADE_PIN configurado se permiten (modo desarrollo) con aviso en el log.
from core.http import rate_limit as _rate_limit_early  # noqa: E402 — se importa de nuevo abajo
from core.pin import require_operator as _require_operator  # noqa: E402

_SAFE_PATH_SEG = re.compile(r'^[A-Za-z0-9_\-]{1,80}$')


def _voice_override_off():
    return jsonify({'error': 'ELEVENLABS_ALLOW_OVERRIDE no está activo',
                    'error_en': 'ELEVENLABS_ALLOW_OVERRIDE is not enabled'}), 403


@app.route('/api/voice/adopt', methods=['POST'])
@_rate_limit_early(limit=10, window=3600)
@_require_operator
def voice_adopt():
    """Adopta una voz de la biblioteca compartida a la cuenta (paso previo a
    asignarla al agente). Mismo candado que agent-tune + PIN de operador. Body:
    {public_owner_id, voice_id, name}."""
    if os.getenv('ELEVENLABS_ALLOW_OVERRIDE', '').strip() not in ('1', 'true', 'yes'):
        return _voice_override_off()
    if not ELEVENLABS_KEY:
        return jsonify({'error': 'ELEVENLABS_KEY no configurada', 'error_en': 'ELEVENLABS_KEY is not set'}), 400
    b = request.get_json(silent=True)
    b = b if isinstance(b, dict) else {}
    po, vid, name = b.get('public_owner_id'), b.get('voice_id'), (b.get('name') or 'Khipu ES')
    if not po or not vid:
        return jsonify({'error': 'public_owner_id y voice_id requeridos',
                        'error_en': 'public_owner_id and voice_id are required'}), 400
    po, vid = str(po), str(vid)
    if not (_SAFE_PATH_SEG.match(po) and _SAFE_PATH_SEG.match(vid)):    # van en la URL de ElevenLabs
        return jsonify({'error': 'public_owner_id / voice_id inválidos',
                        'error_en': 'invalid public_owner_id / voice_id'}), 400
    try:
        r = requests.post(f'https://api.elevenlabs.io/v1/voices/add/{po}/{vid}',
                          headers={'xi-api-key': ELEVENLABS_KEY,
                                   'Content-Type': 'application/json'},
                          json={'new_name': str(name)[:60]}, timeout=12)
        if not r.ok:
            return jsonify({'error': f'ElevenLabs respondió HTTP {r.status_code}',
                            'error_en': f'ElevenLabs returned HTTP {r.status_code}', 'body': r.text[:200]}), 502
        return jsonify({'ok': True, **(r.json() or {})})
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'No se pudo contactar con ElevenLabs', 'error_en': 'Could not reach ElevenLabs',
                        'detail': _diag_redact(e)[:160]}), 502


@app.route('/api/voice/agent-tune', methods=['POST'])
@_rate_limit_early(limit=10, window=3600)
@_require_operator
def voice_agent_tune():
    """Ajuste FINO del agente (modelo TTS / idioma / voice_id). Requiere
    ELEVENLABS_ALLOW_OVERRIDE=1 (mismo candado que el sync del prompt) + PIN de
    operador. Solo toca los campos enviados; devuelve antes/después."""
    if os.getenv('ELEVENLABS_ALLOW_OVERRIDE', '').strip() not in ('1', 'true', 'yes'):
        return _voice_override_off()
    if not (ELEVENLABS_KEY and ELEVENLABS_AGENT_ID):
        return jsonify({'error': 'ELEVENLABS_KEY/AGENT_ID no configurados',
                        'error_en': 'ELEVENLABS_KEY/AGENT_ID are not set'}), 400
    body = request.get_json(silent=True)
    body = body if isinstance(body, dict) else {}
    tts = {}
    if body.get('tts_model'):
        tts['model_id'] = str(body['tts_model'])[:60]
    if body.get('voice_id'):
        tts['voice_id'] = str(body['voice_id'])[:60]
    agent = {}
    if body.get('language'):
        agent['language'] = str(body['language'])[:8]
    if not tts and not agent:
        return jsonify({'error': 'nada que ajustar (tts_model / voice_id / language)',
                        'error_en': 'nothing to tune (tts_model / voice_id / language)'}), 400
    patch = {'conversation_config': {}}
    if tts:
        patch['conversation_config']['tts'] = tts
    if agent:
        patch['conversation_config']['agent'] = agent
    try:
        r = requests.patch(f'https://api.elevenlabs.io/v1/convai/agents/{ELEVENLABS_AGENT_ID}',
                           headers={'xi-api-key': ELEVENLABS_KEY,
                                    'Content-Type': 'application/json'},
                           json=patch, timeout=12)
        if not r.ok:
            return jsonify({'error': f'ElevenLabs respondió HTTP {r.status_code}',
                            'error_en': f'ElevenLabs returned HTTP {r.status_code}', 'body': r.text[:200]}), 502
        return jsonify({'ok': True, 'applied': patch})
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'No se pudo contactar con ElevenLabs', 'error_en': 'Could not reach ElevenLabs',
                        'detail': _diag_redact(e)[:160]}), 502

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

# Config compartida server/ontology (keys de IA, Finnhub, timeout) → core/config.py
# Helpers compartidos: cascada de IA, quote crudo y GET saneado → core/*.py
from core.config import (AI_MODEL, AI_ORDER, CLAUDE, FINNHUB, GEMINI_KEY,
                         GEMINI_MODEL, HTTP_TIMEOUT, NVIDIA_KEY, NVIDIA_MODEL)
from core.http import _rate_buckets, _rate_limit, _safe_get, _safe_ticker, rate_limit, redact_secrets
# PIN de operador ÚNICO (auditoría #7): mismo contador por IP/global para
# /api/trade/*, /api/brokerage/* y /api/mcp/* — ver core/pin.py.
from core.pin import (client_ip as _client_ip, insecure_production_secret as _insecure_prod_secret,
                      require_pin as _require_pin, secret_key_default as _secret_key_default)
from core.ai import (_ai_complete, _ai_configured, _claude_complete,
                     _complete_gemini, _complete_nvidia, _extract_json)
from core.quotes import _fetch_quote_raw

FMP      = os.getenv('FMP_KEY', '')
MSTACK   = os.getenv('MARKETSTACK_KEY', '')

# ── Grafo de Conocimiento Temporal (Neo4j opcional) ─────────────────────────
def _clean_env(v):
    """Limpia un valor de variable de entorno: quita espacios/saltos de línea y
    comillas que se cuelan al pegar en el panel de Railway (causa típica de un
    'Unauthorized' de Neo4j aunque la contraseña sea 'correcta')."""
    v = (v or '').strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        v = v[1:-1].strip()
    return v

# Guardamos también los valores crudos para detectar si venían con espacios.
_NEO4J_URI_RAW      = os.getenv('NEO4J_URI', '')
_NEO4J_USER_RAW     = os.getenv('NEO4J_USER', 'neo4j')
_NEO4J_PASSWORD_RAW = os.getenv('NEO4J_PASSWORD', '')
NEO4J_URI      = _clean_env(_NEO4J_URI_RAW)
NEO4J_USER     = _clean_env(_NEO4J_USER_RAW) or 'neo4j'
NEO4J_PASSWORD = _clean_env(_NEO4J_PASSWORD_RAW)


def _neo4j_available():
    try:
        import neo4j  # noqa: F401  (driver oficial, ligero)
        return True
    except Exception:  # noqa: BLE001
        return False


def _temporal_mode():
    return 'neo4j' if (NEO4J_URI and NEO4J_PASSWORD and _neo4j_available()) else 'native'

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
# framing, plugins y manipulación de <base>. connect-src queda en https:/wss:
# porque la app abre WebSockets directos a Finnhub/ElevenLabs y, en standalone,
# el navegador habla directo con varias APIs. 'unsafe-inline' es necesario: la
# app usa estilos y manejadores onclick inline en miles de elementos.
# upgrade-insecure-requests se añade aparte, solo bajo HTTPS (no rompe dev local).
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
        "https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' data: https://fonts.gstatic.com; "
    "img-src 'self' data: blob: https:; "
    "connect-src 'self' https: wss:; "
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
                                           NEO4J_PASSWORD, SECRET_KEY))


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
    '"name":"Khipus Finance AI","short_name":"Khipu","display":"standalone",'
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
    # para la Sala de Situación geopolítica (engine/geosituation.js)
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
    resp = jsonify(snap)
    # Cambia poco → cacheable, pero versionado para invalidar al editarlo.
    resp.headers['Cache-Control'] = 'public, max-age=300'
    resp.headers['ETag'] = f'"vocab-{snap.get("version", 0)}"'
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
        'app': 'Khipus Finance AI',
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
        'ai_model': AI_MODEL,
        # Auditoría #15: SECRET_KEY por defecto = firmas falsificables. Solo el
        # booleano (nunca el valor); la UI/🩺 lo muestran como alerta.
        'secret_key_default': _secret_key_default(),
        'ts': int(time.time()),
    })


# ----------------------------------------------------------------------------
# Diagnóstico EN VIVO — prueba real de cada integración (no solo bool(key))
# Cada check hace una llamada ligera y reporta ok / latencia / error real.
# NUNCA expone el valor de las keys; los errores se sanitizan.
# ----------------------------------------------------------------------------
_DIAG_CACHE = {'ts': 0.0, 'data': None}
_DIAG_TTL = 60  # segundos


def _diag_redact(text):
    """Quita cualquier valor de key que pudiera aparecer en un mensaje de error:
    TODAS las env secretas (core.http.SECRET_ENV_NAMES: Gemini, NVIDIA, Alpaca,
    TRADE_PIN, KHIPU_ADMIN_SECRET, Tavily…) + los valores ya cargados aquí +
    patrones genéricos (key=/token=/apikey=/secret=, Bearer, x-goog-api-key…).
    Se redacta el texto COMPLETO y luego se trunca (antes se truncaba primero y
    un secreto cortado en el borde quedaba a medias sin tapar)."""
    return redact_secrets(text, extra=(CLAUDE, ELEVENLABS_KEY, FINNHUB, FMP, MSTACK, AV_KEY, SECRET_KEY,
                                       NEO4J_PASSWORD, NEO4J_URI, GEMINI_KEY, NVIDIA_KEY, ALPACA_KEY,
                                       ALPACA_SECRET, TRADE_PIN, KHIPU_ADMIN_SECRET),
                          limit=200)


def _diag_claude():
    if not CLAUDE:
        return {'configured': False, 'ok': False,
                'detail': 'ANTHROPIC_KEY no está en las variables del servidor (Railway). '
                          'Sin ella: Canvas IA, análisis de Khipu y el fallback del War-Room fallan.'}
    t0 = time.time()
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=CLAUDE, timeout=20, max_retries=0)

        def _ping_model(mid):
            _p = dict(model=mid, max_tokens=1, messages=[{'role': 'user', 'content': 'ping'}])
            try:
                m = client.messages.create(thinking={'type': 'disabled'}, **_p)
            except TypeError:
                m = client.messages.create(**_p)
            return m.model

        # Prueba explícita del modelo FAST y del DEEP (sonnet-5) por separado,
        # para diagnosticar exactamente cuál acepta la key.
        from core.config import AI_MODEL_FAST, AI_MODEL_DEEP
        res, oks = {}, []
        for label, mid in (('fast', AI_MODEL_FAST), ('deep', AI_MODEL_DEEP)):
            try:
                res[label] = f'{mid} ✓ ({_ping_model(mid)})'
                oks.append(label)
            except Exception as e:  # noqa: BLE001
                res[label] = f'{mid} ✗ ({_diag_redact(e)})'
        detail = 'FAST: ' + res['fast'] + ' · DEEP: ' + res['deep']
        if not oks:
            # Los dos niveles fallaron: la causa suele ser una sola (saldo,
            # key, modelo retirado). Se dice una vez, en claro.
            detail += _ai_error_hint(res['fast'] + ' ' + res['deep'],
                                     AI_MODEL_FAST, 'AI_MODEL_FAST/AI_MODEL_DEEP')
        return {'configured': True, 'ok': bool(oks), 'latency_ms': int((time.time() - t0) * 1000),
                'detail': detail}
    except Exception as e:  # noqa: BLE001
        return {'configured': True, 'ok': False, 'latency_ms': int((time.time() - t0) * 1000),
                'detail': 'Key presente pero la API rechazó la llamada: ' + _diag_redact(e)}


def _ai_error_hint(err_text, modelo, env_var):
    """Traduce el error crudo de un proveedor de IA a algo accionable.

    Un '404'/'410' pelado no le dice a nadie qué hacer. Los proveedores RETIRAN
    modelos: pasó en sept-2026 con gemini-2.0-flash (404) y
    meta/llama-3.1-70b-instruct (410) a la vez, dejando la app sin respaldo.
    El arreglo nunca es tocar código — es cambiar la variable de entorno."""
    s = str(err_text)
    if '404' in s or '410' in s or 'not found' in s.lower() or 'not_found' in s.lower():
        return (f' → El modelo «{modelo}» ya no existe en el proveedor (retirado). '
                f'Arreglo: pon {env_var} en Railway con un modelo vigente de su catálogo. '
                f'No hace falta desplegar.')
    if '401' in s or '403' in s or 'api key' in s.lower() or 'unauthorized' in s.lower():
        return ' → La key parece inválida o sin permisos para ese modelo.'
    if '429' in s or 'quota' in s.lower() or 'rate' in s.lower():
        return ' → Límite de uso alcanzado (cuota o rate-limit). Espera o sube el plan.'
    if 'credit' in s.lower() or 'balance' in s.lower() or 'billing' in s.lower():
        return ' → Saldo agotado: recarga en la consola del proveedor.'
    return ''


def _diag_gemini():
    if not GEMINI_KEY:
        return {'configured': False, 'ok': False,
                'detail': 'GEMINI_KEY no está. (Opcional) Canal de respaldo de IA — Google Gemini.'}
    t0 = time.time()
    try:
        txt, model = _complete_gemini('', 'ping', 1)
        return {'configured': True, 'ok': True, 'latency_ms': int((time.time() - t0) * 1000),
                'detail': f'Key válida — {model} respondió.'}
    except Exception as e:  # noqa: BLE001
        from core.config import GEMINI_MODEL
        red = _diag_redact(e)
        return {'configured': True, 'ok': False, 'latency_ms': int((time.time() - t0) * 1000),
                'detail': 'Gemini rechazó la llamada: ' + red
                          + _ai_error_hint(red, GEMINI_MODEL, 'GEMINI_MODEL')}


def _diag_nvidia():
    if not NVIDIA_KEY:
        return {'configured': False, 'ok': False,
                'detail': 'NVIDIA_KEY no está. (Opcional) Canal de respaldo de IA — NVIDIA NIM (gratis para MVP).'}
    t0 = time.time()
    try:
        txt, model = _complete_nvidia('', 'ping', 1)
        return {'configured': True, 'ok': True, 'latency_ms': int((time.time() - t0) * 1000),
                'detail': f'Key válida — {model} respondió.'}
    except Exception as e:  # noqa: BLE001
        from core.config import NVIDIA_MODEL
        red = _diag_redact(e)
        return {'configured': True, 'ok': False, 'latency_ms': int((time.time() - t0) * 1000),
                'detail': 'NVIDIA rechazó la llamada: ' + red
                          + _ai_error_hint(red, NVIDIA_MODEL, 'NVIDIA_MODEL')}


def _diag_elevenlabs():
    if not ELEVENLABS_KEY:
        return {'configured': False, 'ok': False, 'agent_configured': bool(ELEVENLABS_AGENT_ID),
                'detail': 'ELEVENLABS_KEY no está en el servidor. Khipu (voz) no podrá conectar.'}
    t0 = time.time()
    try:
        r = requests.get('https://api.elevenlabs.io/v1/user',
                         headers={'xi-api-key': ELEVENLABS_KEY}, timeout=8)
        lat = int((time.time() - t0) * 1000)
        if not r.ok:
            return {'configured': True, 'ok': False, 'agent_configured': bool(ELEVENLABS_AGENT_ID),
                    'latency_ms': lat,
                    'detail': f'Key inválida o sin permisos (HTTP {r.status_code}).'}
        agent_ok = None
        if ELEVENLABS_AGENT_ID:
            try:
                ra = requests.get(
                    f'https://api.elevenlabs.io/v1/convai/agents/{ELEVENLABS_AGENT_ID}',
                    headers={'xi-api-key': ELEVENLABS_KEY}, timeout=8)
                agent_ok = ra.ok
            except Exception:  # noqa: BLE001
                agent_ok = False
        if not ELEVENLABS_AGENT_ID:
            detail = 'Key válida, pero falta ELEVENLABS_AGENT_ID — Khipu no sabe a qué agente conectar.'
            ok = False
        elif agent_ok:
            detail = 'Key válida y agente encontrado. Khipu debería conectar.'
            ok = True
        else:
            detail = 'Key válida, pero el ELEVENLABS_AGENT_ID no existe o no es accesible con esta key.'
            ok = False
        return {'configured': True, 'ok': ok, 'agent_configured': bool(ELEVENLABS_AGENT_ID),
                'agent_ok': agent_ok, 'latency_ms': lat, 'detail': detail}
    except Exception as e:  # noqa: BLE001
        return {'configured': True, 'ok': False, 'agent_configured': bool(ELEVENLABS_AGENT_ID),
                'latency_ms': int((time.time() - t0) * 1000),
                'detail': 'No se pudo contactar ElevenLabs: ' + _diag_redact(e)}


def _db_error_hint(err_text):
    """Traduce un error de conexión a base de datos a algo accionable.

    Mismo criterio que `_ai_error_hint`: un traceback de psycopg2 no le dice a
    nadie qué hacer. El caso real (sept-2026): DATABASE_URL apuntaba a
    'postgres.railway.internal' — el host de la red privada de Railway — pero
    el servicio Postgres ya no existía con ese nombre, así que el DNS interno
    no resolvía. Un texto literal en la variable envejece; una REFERENCIA
    (${{Postgres.DATABASE_URL}}) la resuelve Railway sola y nunca se queda
    obsoleta."""
    s = str(err_text).lower()
    if 'railway.internal' in s and ('translate host name' in s or 'name or service not known' in s):
        return (' → El servicio de base de datos no existe con ese nombre en el proyecto. '
                'En Railway: crea el Postgres (+ New → Database) y pon la variable como '
                'REFERENCIA, no como texto: DATABASE_URL = ${{Postgres.DATABASE_URL}} '
                '(usa el nombre EXACTO que aparece en la tarjeta del servicio). '
                'Así Railway la resuelve sola y no vuelve a quedarse obsoleta.')
    if 'translate host name' in s or 'name or service not known' in s or 'nodename nor servname' in s:
        return (' → El host de la base de datos no resuelve: el servidor no existe, cambió de '
                'nombre, o la instancia gratuita se borró por inactividad.')
    if 'password authentication failed' in s or 'authentication' in s:
        return ' → El host responde pero las credenciales no son válidas: revisa usuario/contraseña.'
    if 'does not exist' in s and 'database' in s:
        return ' → El servidor responde pero esa base de datos no existe.'
    if 'connection refused' in s:
        return ' → El host resuelve pero nadie escucha en ese puerto: ¿el servicio está apagado?'
    if 'timeout' in s or 'timed out' in s:
        return ' → Tiempo de espera agotado: red o firewall entre la app y la base.'
    return ''


def _diag_ontologia():
    """Ontología (Postgres, Fase 1 del roadmap): fuente única de verdad de
    objetos/vínculos con historia bitemporal. Feature opcional — si
    DATABASE_URL no está configurada, el resto de la app sigue igual."""
    try:
        from ontology.db import ontology_available
        if not ontology_available():
            return {'configured': False, 'ok': True,
                    'detail': 'Ontología no configurada (opcional). Añade el plugin de Postgres en '
                              'Railway y DATABASE_URL para activar /api/ontology/*.'}
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
                return {'configured': True, 'ok': False,
                        'detail': f'Esquema desactualizado: faltan {", ".join(faltantes)}. '
                                  'Se intentó reparar automáticamente y no se pudo — '
                                  'reinicia el servicio en Railway (Deployments → Restart).'}
            log.warning('Esquema de la ontología reparado en caliente: %s', faltantes)

        from ontology.db import session_scope
        from ontology.models import ObjectRecord, LinkRecord, Event
        with session_scope() as s:
            n_obj = s.query(ObjectRecord).count()
            n_link = s.query(LinkRecord).count()
            n_ev = s.query(Event).count()
            last_ev = s.query(Event).order_by(Event.recorded_at.desc()).first()
        lineage = f' · último evento: {last_ev.recorded_at.strftime("%Y-%m-%d %H:%M UTC")} ({last_ev.source})' if last_ev else ''
        return {'configured': True, 'ok': True,
                'detail': f'Ontología activa — {n_obj} objetos, {n_link} vínculos, {n_ev} eventos.{lineage}'}
    except Exception as e:  # noqa: BLE001
        red = _diag_redact(e)
        return {'configured': True, 'ok': False,
                'detail': 'Ontología configurada pero no conecta: ' + red + _db_error_hint(red)}


def _diag_grafo():
    mode = _temporal_mode()
    if mode == 'native':
        return {'configured': True, 'ok': True,
                'detail': 'Grafo de Conocimiento Temporal en modo NATIVO (client-side + memoria). '
                          'Añade NEO4J_URI/USER/PASSWORD para memoria persistente en Neo4j.'}
    # neo4j mode → probar conexión. Mostramos usuario + host (seguros) para
    # depurar el Unauthorized sin exponer la contraseña.
    host = ''
    try:
        host = NEO4J_URI.split('://', 1)[-1].split('@')[-1].split('/')[0]
    except Exception:  # noqa: BLE001
        host = '(uri inválida)'
    ctx = f' [usuario={NEO4J_USER} · host={host} · pw={len(NEO4J_PASSWORD)} car.]'
    warn = ''
    if _NEO4J_PASSWORD_RAW != _NEO4J_PASSWORD_RAW.strip():
        warn += ' ⚠ la contraseña tenía espacios (ya la limpié, pero revísala).'
    t0 = time.time()
    try:
        drv = _get_neo4j_driver()
        drv.verify_connectivity()
        return {'configured': True, 'ok': True, 'latency_ms': int((time.time() - t0) * 1000),
                'detail': 'Neo4j conectado — memoria temporal persistente activa.' + ctx}
    except Exception as e:  # noqa: BLE001
        return {'configured': True, 'ok': False, 'latency_ms': int((time.time() - t0) * 1000),
                'detail': 'NEO4J configurado pero no conecta: ' + _diag_redact(e)
                          + _db_error_hint(_diag_redact(e)) + ctx + warn}


def _diag_alpaca():
    """Bróker: configurado, alcanzable y — LO MÁS IMPORTANTE para un usuario no
    técnico — en qué modo está: PAPEL (simulado) o REAL. Auditoría Track D: era
    el gap de seguridad/UX más grande (no había forma de verlo dentro de la app)."""
    mode = 'paper' if 'paper-api' in ALPACA_BASE else 'live'
    if not ALPACA_KEY:
        return {'configured': False, 'ok': False, 'mode': mode,
                'detail': 'ALPACA_KEY sin configurar — el bróker simulado está apagado.'}
    try:
        r = requests.get(f'{ALPACA_BASE}/v2/account', headers=_alpaca_hdrs(), timeout=8)
        ok = r.status_code == 200
        detail = ('Cuenta PAPEL (simulada) conectada — sin dinero real.' if ok and mode == 'paper'
                  else '⚠ Cuenta REAL conectada — las órdenes mueven dinero de verdad.' if ok
                  else f'Alpaca respondió HTTP {r.status_code}.')
        return {'configured': True, 'ok': ok, 'mode': mode, 'detail': detail}
    except Exception as e:  # noqa: BLE001
        return {'configured': True, 'ok': False, 'mode': mode,
                'detail': f'Alpaca inalcanzable: {str(e)[:100]}'}


def _diag_finnhub():
    if not FINNHUB:
        return {'configured': False, 'ok': False,
                'detail': 'FINNHUB_KEY no está. Los precios en vivo del terminal no cargarán.'}
    t0 = time.time()
    try:
        r = requests.get(f'https://finnhub.io/api/v1/quote?symbol=AAPL&token={FINNHUB}', timeout=6)
        lat = int((time.time() - t0) * 1000)
        if r.ok:
            c = (r.json() or {}).get('c')
            if isinstance(c, (int, float)) and c > 0:
                return {'configured': True, 'ok': True, 'latency_ms': lat,
                        'detail': f'Key válida — cotización AAPL ${c} OK.'}
            return {'configured': True, 'ok': False, 'latency_ms': lat,
                    'detail': 'Key responde pero sin datos (¿límite de plan agotado?).'}
        return {'configured': True, 'ok': False, 'latency_ms': lat,
                'detail': f'Finnhub HTTP {r.status_code} — key inválida o rate-limited.'}
    except Exception as e:  # noqa: BLE001
        return {'configured': True, 'ok': False, 'latency_ms': int((time.time() - t0) * 1000),
                'detail': 'No se pudo contactar Finnhub: ' + _diag_redact(e)}


@app.route('/api/ai/debug')
@rate_limit(limit=20, window=300)
def ai_debug():
    """Depuración: ejecuta _ai_complete con un prompt real (tier configurable) y
    reporta AI_ORDER, los modelos resueltos y el error/modelo real — sin exponer
    claves. Para diagnosticar por qué la sim usa NVIDIA en vez de Sonnet 5."""
    from core import ai as _ai
    from core.config import AI_ORDER as _ORDER, AI_MODEL_FAST as _F, AI_MODEL_DEEP as _D
    tier = 'deep' if request.args.get('tier') == 'deep' else 'fast'
    out = {'ai_order': _ORDER, 'model_fast': _F, 'model_deep': _D, 'tier': tier}
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
        return jsonify(out)

    services = {
        'claude':     _diag_claude(),
        'gemini':     _diag_gemini(),
        'nvidia':     _diag_nvidia(),
        'elevenlabs': _diag_elevenlabs(),
        'finnhub':    _diag_finnhub(),
        'grafo':      _diag_grafo(),
        'ontologia':  _diag_ontologia(),
        'alpaca':     _diag_alpaca(),
    }
    # Secundarias: solo presencia (no gastamos llamadas externas extra)
    _extra_names = [n for n, v in (('FMP', FMP), ('MarketStack', MSTACK), ('AlphaVantage', AV_KEY)) if v]
    services['market_extra'] = {
        'configured': bool(_extra_names),
        'ok': bool(_extra_names),
        'detail': ('Fuentes de respaldo activas: ' + ', '.join(_extra_names) + '.') if _extra_names
                  else 'Ninguna fuente de respaldo configurada (el mercado depende solo de Finnhub).',
    }

    n_ok = sum(1 for s in services.values() if s.get('ok'))
    out = {
        'ts': int(now), 'cached': False, 'ai_model': AI_MODEL,
        'jwt_api': _HAS_JWT, 'services': services,
        'summary': {'ok': n_ok, 'total': len(services)},
        'secret_key_default': _secret_key_default(),
        'security_warnings': _security_warnings(),
    }
    _DIAG_CACHE['ts'] = now
    _DIAG_CACHE['data'] = out
    return jsonify(out)


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


@app.route('/api/quote/<ticker>')
@rate_limit(limit=120, window=60)
@cache.cached(timeout=15, query_string=True)
def quote(ticker):
    if not FINNHUB:
        return jsonify({'error': 'no FINNHUB_KEY'}), 400
    ticker = _safe_ticker(ticker)
    if not ticker:
        return jsonify({'error': 'invalid ticker'}), 400
    data, err = _fetch_quote_raw(ticker)
    if err:
        return jsonify({'error': err}), 502
    return jsonify(data)


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
    return jsonify({
        'market': market_registry().statuses(),
        'crypto': crypto_registry().statuses(),
        'news': news_registry().statuses(),
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
    from core.quotes import fetch_quote_intl, is_intl
    tickers = [s for s in (_safe_ticker(t) for t in request.args.get('symbols', '').split(',')) if s]
    if not FINNHUB and not any(is_intl(t) for t in tickers):
        return jsonify({'error': 'no FINNHUB_KEY'}), 400
    results = {}
    for t in tickers[:60]:  # límite de cortesía por request
        # Bolsas no-EEUU (688825.SS, 1347.HK, 6239.TW…): Yahoo + conversión a
        # USD, en la MISMA forma cruda {c, pc, v} que espera el cliente.
        # No requieren FINNHUB_KEY.
        if is_intl(t):
            q = fetch_quote_intl(t)
            if q:
                results[t] = {'c': q['live'], 'pc': q['prev'], 'v': q['vol'],
                              'currency': q['currency'], 'converted': q['converted']}
            continue
        if not FINNHUB:
            continue
        data, err = _fetch_quote_raw(t, timeout=4)
        if data:
            results[t] = data
    return jsonify(results)


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
MAX_ORDER_USD = 100000.0           # tope por orden (notional o qty × precio)
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


def _trading_halted_response():
    return jsonify({'error': 'Interruptor general APAGADO (BROKERAGE_TRADING_ENABLED=off): no se envía ninguna orden',
                    'error_en': 'Master switch OFF (BROKERAGE_TRADING_ENABLED=off): no orders are sent',
                    'code': 'trading_halted'}), 423


def _broker_missing_response():
    return jsonify({'error': 'Bróker no configurado: faltan ALPACA_KEY/ALPACA_SECRET en Railway',
                    'error_en': 'Broker not configured: ALPACA_KEY/ALPACA_SECRET missing in Railway',
                    'code': 'broker_not_configured'}), 400


def _trade_actor():
    try:
        a = str(request.headers.get('X-Khipu-Actor') or '').strip()[:80]
    except Exception:  # noqa: BLE001 — fuera de una petición (hilo del agente)
        a = ''
    return f'{a} (PIN)' if a else 'ui (PIN)'


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


def _house_price(sym):
    """Último precio (USD) para acotar qty × precio. None si no se pudo verificar."""
    try:
        if '/' in sym:
            r = requests.get('https://data.alpaca.markets/v1beta3/crypto/us/latest/trades',
                             params={'symbols': sym}, headers=_alpaca_hdrs(), timeout=6)
            p = (((_alpaca_json(r) or {}).get('trades') or {}).get(sym) or {}).get('p')
            return float(p) if p and float(p) > 0 else None
        if FINNHUB:
            data, err = _fetch_quote_raw(sym, timeout=5)
            if not err and data and float(data.get('c') or 0) > 0:
                return float(data['c'])
        from urllib.parse import quote as _q
        r = requests.get(f'https://data.alpaca.markets/v2/stocks/{_q(sym, safe="")}/trades/latest',
                         headers=_alpaca_hdrs(), timeout=6)
        p = ((_alpaca_json(r) or {}).get('trade') or {}).get('p')
        return float(p) if p and float(p) > 0 else None
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
        return jsonify(dict(cached, cached=True))
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
            info['hint'] = 'No se pudo conectar con Alpaca — revisa ALPACA_BASE.'
            info['hint_en'] = 'Could not reach Alpaca — check ALPACA_BASE.'
    _TRADE_STATUS_CACHE.update(ts=now, data=info)
    return jsonify(info)


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


@app.route('/api/trade/close', methods=['POST'])
@rate_limit(limit=30, window=60)
@_trade_auth
def trade_close():
    """Cierra por completo UNA posición (1-clic 'CLOSE' del scalping). Alpaca:
    DELETE /v2/positions/{symbol} (cripto va SIN barra en el path: BTCUSD).
    Auditoría #8: el símbolo se valida estricto y va url-encodeado — antes '.'
    o '?cancel_orders=true' podían acabar en DELETE /v2/positions (= cerrar TODO)."""
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
    from urllib.parse import quote as _q
    path_sym = _q(symbol.replace('/', ''), safe='')   # Alpaca usa BTCUSD en el path de posiciones
    try:
        r = requests.delete(f'{ALPACA_BASE}/v2/positions/{path_sym}', headers=_alpaca_hdrs(), timeout=10)
    except Exception as e:  # noqa: BLE001
        _trade_audit('trade_close', {'symbol': symbol, 'outcome': 'error', 'error': type(e).__name__})
        return _bad('No se pudo contactar con Alpaca', 'Could not reach Alpaca', code='broker_unreachable',
                    status=502, detail=_diag_redact(e))
    payload = _alpaca_json(r)
    if payload is None:
        payload = {'ok': r.status_code < 300}
    ok = 200 <= r.status_code < 300
    _trade_audit('trade_close', {'symbol': symbol, 'outcome': 'submitted' if ok else 'rejected',
                                 'http_status': r.status_code,
                                 'alpaca_order_id': (payload.get('id') if isinstance(payload, dict) else None),
                                 'alpaca_message': (str(payload.get('message'))[:160]
                                                    if isinstance(payload, dict) and payload.get('message') else None)})
    if isinstance(payload, dict):
        payload.setdefault('paper', _paper())
    return jsonify(payload), r.status_code


@app.route('/api/trade/order', methods=['POST'])
@rate_limit(20, 60)
@_trade_auth
def trade_order():
    """Orden de la cuenta de la casa (Alpaca). Auditoría #9/#21:
    · tope $100.000 por orden en notional O en qty × precio (limit_price, o el
      último precio si es market; sin precio verificable → se rechaza);
    · limit_price numérico > 0; time_in_force ∈ day|gtc|ioc|fok (cripto → gtc);
    · client_order_id (UUID del cliente) se reenvía a Alpaca: un reintento o el
      doble clic voz+botón NO duplica la orden (Alpaca la rechaza como repetida
      y aquí se devuelve la ya existente con duplicate=true);
    · interruptor BROKERAGE_TRADING_ENABLED=off → 423 'trading_halted';
    · cada intento queda en broker_audit (o en el log sin base)."""
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
    is_crypto = '/' in ticker
    if is_crypto:
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
            return reject('notional fuera de rango: mínimo $1, máximo $100,000 por orden',
                          'notional out of range: minimum $1, maximum $100,000 per order', 'over_cap')
        est_usd = notional
    else:
        q = _finite_pos(qty)
        if q is None or _num_str(q) in ('', '0'):      # 1e-10 → '0' en Alpaca: se rechaza aquí
            return reject('qty debe ser un número mayor que 0 (hasta 9 decimales)',
                          'qty must be a number greater than 0 (up to 9 decimals)')
        if q > 1e7:
            return reject('qty demasiado grande', 'qty too large', 'over_cap')
        # Monto a acotar: una COMPRA limit se llena a ≤ limit_price → qty × limit
        # es el techo. Una VENTA limit se llena a ≥ limit_price: con el limit muy
        # por debajo del mercado se llena AL MERCADO → el techo es qty × max(limit,
        # mercado); sin precio de mercado verificable se rechaza (como market).
        if otype == 'limit' and side == 'buy':
            px = limit_price
        else:
            mkt = _house_price(ticker)
            px = None if mkt is None else (max(mkt, limit_price) if otype == 'limit' else mkt)
        if px is None:
            return reject('No se pudo verificar el precio de mercado para acotar el monto: usa notional (USD)'
                          + (' o una orden limit de compra' if side == 'buy' else ''),
                          'Could not verify the market price to cap the amount: use notional (USD)'
                          + (' or a buy limit order' if side == 'buy' else ''),
                          'price_unavailable', 422)
        est_usd = q * px
        if est_usd > MAX_ORDER_USD:
            return reject(f'La orden supera el tope de $100,000 (≈ ${est_usd:,.0f})',
                          f'The order exceeds the $100,000 cap (≈ ${est_usd:,.0f})', 'over_cap')
        qty = q
    summary['est_usd'] = round(est_usd, 2)
    if not _house_trading_enabled():
        _trade_audit('trade_order', dict(summary, outcome='blocked_kill_switch'))
        return _trading_halted_response()
    body = {'symbol': ticker, 'side': side, 'type': otype, 'time_in_force': tif, 'client_order_id': coid}
    if notional is not None:
        body['notional'] = f'{notional:.2f}'
    else:
        body['qty'] = _num_str(qty)
    if otype == 'limit':
        body['limit_price'] = _num_str(limit_price)
    try:
        r = requests.post(f'{ALPACA_BASE}/v2/orders', headers=_alpaca_hdrs(), json=body, timeout=15)
    except Exception as e:  # noqa: BLE001
        # Estado DESCONOCIDO (timeout): la orden pudo llegar. Reintentar con el
        # MISMO client_order_id es seguro — Alpaca no la duplica.
        _trade_audit('trade_order', dict(summary, outcome='unknown_error', error=type(e).__name__))
        return _bad('No se pudo confirmar con Alpaca; reintenta con el mismo client_order_id o revisa el historial',
                    'Could not confirm with Alpaca; retry with the same client_order_id or check the history',
                    code='broker_unreachable', status=502, client_order_id=coid)
    payload = _alpaca_json(r)
    if payload is None:
        _trade_audit('trade_order', dict(summary, outcome='error', http_status=r.status_code))
        return _bad(f'Alpaca respondió HTTP {r.status_code} sin JSON', f'Alpaca answered HTTP {r.status_code} without JSON',
                    code='broker_bad_response', status=502, client_order_id=coid)
    if r.status_code == 422 and 'client_order_id' in json.dumps(payload).lower():
        # Repetida (reintento/doble clic): devolver la orden que YA existe.
        try:
            r2 = requests.get(f'{ALPACA_BASE}/v2/orders:by_client_order_id', params={'client_order_id': coid},
                              headers=_alpaca_hdrs(), timeout=10)
            prev = _alpaca_json(r2)
            if r2.status_code == 200 and isinstance(prev, dict) and prev.get('id'):
                prev['duplicate'] = True
                prev['paper'] = _paper()
                _trade_audit('trade_order', dict(summary, outcome='duplicate', alpaca_order_id=prev.get('id')))
                return jsonify(prev), 200
        except Exception:  # noqa: BLE001
            pass
    ok = 200 <= r.status_code < 300
    _trade_audit('trade_order', dict(
        summary, outcome='submitted' if ok else 'rejected', http_status=r.status_code,
        alpaca_order_id=(payload.get('id') if isinstance(payload, dict) else None),
        alpaca_status=(payload.get('status') if isinstance(payload, dict) else None),
        alpaca_message=(str(payload.get('message'))[:160] if isinstance(payload, dict) and payload.get('message')
                        else None)))
    if isinstance(payload, dict):
        payload.setdefault('paper', _paper())
        if not ok:
            payload.setdefault('error', payload.get('message') or f'Alpaca HTTP {r.status_code}')
            payload.setdefault('error_en', payload.get('message') or f'Alpaca HTTP {r.status_code}')
            if 'code' in payload:
                payload['alpaca_code'] = payload['code']       # el código numérico de Alpaca se conserva
            payload['code'] = 'broker_rejected'
    return jsonify(payload), r.status_code


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
        'Eres un analista de criptomercados CAUTO de Khipus Finance AI. '
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
        text, model = _ai_complete(sys, prompt, max_tokens=1400, tier='deep')
        parsed = _extract_json(text)
        if not isinstance(parsed, dict):
            raise ValueError('respuesta no-JSON')
    except Exception as e:  # noqa: BLE001
        return jsonify({'ok': False, 'error': f'IA falló · AI failed: {str(e)[:160]}'}), 502

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


# ── Investigación profunda estructurada (más allá del nodo) — Sonnet 5 deep ──
@app.route('/api/research/deep', methods=['POST'])
@rate_limit(limit=20, window=3600)
def research_deep():
    """{id, lang} → informe estructurado que va MÁS ALLÁ de la empresa: sector,
    competidores, geopolítica, chokepoints de su cadena y una tesis. Cache 15 min."""
    if not _ai_configured():
        return jsonify({'ok': False, 'error': 'no AI provider configured'}), 400
    from core.semantic import build_context, resolve_ids
    body = request.get_json(force=True, silent=True) or {}
    lang = 'en' if str(body.get('lang', 'es')).lower().startswith('en') else 'es'
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
        'Eres el analista jefe de Khipus Finance AI, experto en la cadena de '
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
        text, model = _ai_complete(sys, prompt, max_tokens=2600, tier='deep')
        parsed = _extract_json(text)
        if not isinstance(parsed, dict):
            raise ValueError('respuesta no-JSON')
    except Exception as e:  # noqa: BLE001
        return jsonify({'ok': False, 'error': f'IA falló · AI failed: {str(e)[:160]}'}), 502

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
    try:
        return jsonify({'ok': True, 'limits': ai_usage.save_settings(body.get('limits') or {}, actor)})
    except (TypeError, ValueError) as e:
        return jsonify({'error': f'valor inválido: {str(e)[:80]}', 'error_en': f'invalid value: {str(e)[:80]}'}), 400


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
        text, model = _claude_complete(
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
You are Khipus Finance AI's Canvas AI — an expert at semiconductor / AI / space supply chain analytics.
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
        text, model = _claude_complete(_CANVAS_SYSTEM, prompt, max_tokens=1600, tier='fast')
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


# ── Khipu Command Center — interpreta comando libre → respuesta + acciones ────
_COMMAND_SYSTEM = """\
Eres Khipu, el copiloto de IA del terminal financiero Khipus Finance AI (semiconductores, IA y espacio).
El usuario te habla o escribe en lenguaje natural y tú controlas la app y respondes como analista.
Responde SOLO con JSON válido (sin markdown, sin explicación fuera del JSON):

{"answer":"<respuesta breve y útil en español, 1-3 frases, tono de analista senior>",
 "actions":[{"type":"<tipo>","arg":"<valor>"}]}

Tipos de acción válidos:
• switch_tab   arg ∈ {map, market, analysis, geo, simulation, space, terminal, canvas}
• navigate     arg = node_id exacto (centra esa empresa en el grafo)
• stress       arg = node_id exacto (lanza cascada de fallo de esa empresa)
• simulate     arg = preset_id ∈ {taiwan_conflict, china_chip_ban_total, hbm_shortage_2027, openai_ipo_impact, starshield_reveal}
• chart        arg = una instrucción en lenguaje natural para generar un gráfico/tabla con los datos (ej "compara márgenes de NVIDIA, TSMC y ASML")
• second_brain arg = node_id (abre el panel de inteligencia de esa empresa)

Reglas:
- Usa SIEMPRE node_id exactos de la lista del contexto (no inventes ids).
- Si el pedido menciona canvas, gráfico, graficar, dashboard, tabla, comparar, "muéstrame los datos",
  "top N", ranking, márgenes, riesgo de varias empresas → SIEMPRE devuelve una acción "chart" con
  el arg en lenguaje natural describiendo qué graficar. NO te limites a responder en texto.
- Si pide "analiza X", "navega a X", "qué pasa si cae X" → navigate / stress sobre ese id.
- Si pide una simulación o escenario geopolítico → simulate con el preset más cercano.
- Si es solo una pregunta de conocimiento, responde en "answer" y deja actions vacío (o un switch_tab útil).
- answer SIEMPRE en español, concreto, sin relleno. Máximo 3 frases.
- NUNCA difieras ("ahorita lo hago", "un momento", "lo preparo"): si el pedido implica una
  acción, DEVUÉLVELA YA en "actions" en esta misma respuesta. El answer describe lo que YA hiciste,
  no lo que harás. Si piden graficar/comparar/ver datos, incluye SIEMPRE una acción "chart".
"""


@app.route('/api/ai/command', methods=['POST'])
@rate_limit(limit=80, window=3600)
def ai_command():
    if not _ai_configured():
        return jsonify({'error': 'no AI provider configured',
                        'answer': 'No tengo ninguna IA configurada en el servidor '
                                  '(Claude, Gemini o NVIDIA). Añade al menos una key.', 'actions': []}), 400
    body = request.get_json(force=True, silent=True) or {}
    query = str(body.get('query', ''))[:400].strip()
    if not query:
        return jsonify({'error': 'query is required'}), 400
    nodes_raw = body.get('nodes') or []
    # contexto compacto: id, label, ticker — suficiente para mapear nombres a ids
    nodes_compact = [{'id': n.get('id'), 'label': n.get('label'),
                      'ticker': (n.get('ticker') or n.get('mkt') or '')}
                     for n in nodes_raw[:800]]
    ctx_str = json.dumps({'nodes': nodes_compact, 'selected': body.get('selected')},
                         ensure_ascii=False)
    # Datos de ESPACIO: si preguntan por satélites/constelaciones/lanzamientos, se
    # inyectan los conteos REALES (CelesTrak, cacheado) para que Khipu responda con
    # números en vez de "no sé cuántos satélites tiene Starlink".
    space_ctx = ''
    if re.search(r'sat[eé]lit|constelaci|starlink|oneweb|iridium|[oó]rbit|orbit|lanzamient|launch|espacio|\bspace\b', query, re.I):
        try:
            space_ctx = ('\n\nDATOS DE ESPACIO — conteos REALES y ACTUALES (CelesTrak). '
                         'Úsalos TEXTUALMENTE; NO los contradigas ni los sustituyas por tu '
                         'conocimiento previo, y NO digas que no sabes:\n' + _space_facts_str())
        except Exception:  # noqa: BLE001
            pass
    prompt = f'PEDIDO DEL USUARIO: {query}\n\nCONTEXTO (empresas disponibles):\n{ctx_str}{space_ctx}'
    try:
        text, model = _claude_complete(_COMMAND_SYSTEM, prompt, max_tokens=700)
        data = _extract_json(text)
        if not isinstance(data, dict):
            raise ValueError('not an object')
        actions = data.get('actions') or []
        # saneo: solo tipos conocidos
        valid = {'switch_tab', 'navigate', 'stress', 'simulate', 'chart', 'second_brain'}
        actions = [a for a in actions if isinstance(a, dict) and a.get('type') in valid]
        return jsonify({'answer': str(data.get('answer', ''))[:600],
                        'actions': actions[:4], 'model': model})
    except json.JSONDecodeError:
        # Si Claude no devolvió JSON, al menos devolvemos su texto como respuesta.
        return jsonify({'answer': (text or 'No pude interpretar eso.')[:600], 'actions': []})
    except Exception as e:   # noqa: BLE001
        return jsonify({'error': str(e)[:200],
                        'answer': 'Tuve un problema procesando ese pedido.', 'actions': []}), 500


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


# ── CelesTrak TLE — satélites reales para el Planeta 3D ───────────────────────
# Grupos de CelesTrak → (nombre visible, nodo Khipu vinculado, color hex)
_SAT_GROUPS = [
    ('starlink',      'Starlink',        'SpaceX',           '#ff7a45'),
    ('oneweb',        'OneWeb',          'EutelsatOneWeb',   '#36cfc9'),
    ('planet',        'Planet Labs',     'PlanetLabs',       '#73d13d'),
    ('spire',         'Spire Global',    'Spire',            '#9254de'),
    ('iridium-NEXT',  'Iridium NEXT',    'Iridium',          '#40a9ff'),
    ('globalstar',    'Globalstar',      'Globalstar',       '#f759ab'),
    ('ses',           'SES / O3b',       'SES',              '#ffc53d'),
    ('gps-ops',       'GPS',             None,               '#bfbfbf'),
    ('galileo',       'Galileo',         None,               '#597ef7'),
    ('beidou',        'BeiDou',          None,               '#ff4d4f'),
    ('stations',      'Estaciones (ISS/CSS)', None,          '#ffffff'),
]
# Tope de satélites RENDERIZADOS por grupo (los conteos reportados son los reales).
_SAT_RENDER_CAP = {'starlink': 1200, 'oneweb': 400, 'planet': 250, '_default': 220}


def _parse_tle_text(txt):
    """Parsea formato TLE de 3 líneas → [{name,l1,l2}]."""
    out = []
    lines = [ln.rstrip() for ln in txt.splitlines() if ln.strip()]
    i = 0
    while i + 2 < len(lines) + 1:
        if i + 2 >= len(lines):
            break
        name, l1, l2 = lines[i], lines[i + 1], lines[i + 2]
        if l1.startswith('1 ') and l2.startswith('2 '):
            out.append({'name': name.strip(), 'l1': l1, 'l2': l2})
            i += 3
        else:
            i += 1
    return out


@app.route('/api/space/tle')
@rate_limit(limit=20, window=3600)
@cache.cached(timeout=86400)  # CelesTrak actualiza ~1/día
def space_tle():
    """Satélites reales por constelación (CelesTrak). Muestrea para rendimiento
    pero reporta los conteos REALES. Si CelesTrak no responde, fallback sintético."""
    constellations = []
    sats = []
    any_ok = False
    for idx, (group, label, node, color) in enumerate(_SAT_GROUPS):
        try:
            url = f'https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle'
            r = requests.get(url, timeout=12, headers={'User-Agent': 'KhipuFinance/1.0'})
            if not r.ok or not r.text or '<' in r.text[:1]:
                raise RuntimeError(f'HTTP {r.status_code}')
            parsed = _parse_tle_text(r.text)
            if not parsed:
                raise RuntimeError('sin TLEs')
            any_ok = True
            real_count = len(parsed)
            cap = _SAT_RENDER_CAP.get(group, _SAT_RENDER_CAP['_default'])
            if real_count > cap:
                step = real_count / cap
                sampled = [parsed[int(k * step)] for k in range(cap)]
            else:
                sampled = parsed
            for s in sampled:
                sats.append({'n': s['name'], 'l1': s['l1'], 'l2': s['l2'], 'c': idx})
            constellations.append({
                'name': label, 'count': real_count, 'rendered': len(sampled),
                'node': node, 'color': color,
            })
        except Exception as e:  # noqa: BLE001
            constellations.append({
                'name': label, 'count': 0, 'rendered': 0,
                'node': node, 'color': color, 'error': str(e)[:60],
            })

    if not any_ok:
        # Fallback sintético (p.ej. red sin egress a CelesTrak): órbitas plausibles.
        # NO se cachea (antes quedaba 24 h aunque CelesTrak volviera).
        return _degraded(jsonify(_fallback_tle()))

    total = sum(c['count'] for c in constellations)
    # comparte los conteos REALES con el Khipu de TEXTO (para que reuse estos
    # números y no haga su propio re-fetch parcial que dejaba a Starlink en 0).
    try:
        cache.set('space_constellations',
                  [(c['name'], c['count'], True) for c in constellations if c.get('count')], timeout=86400)
    except Exception:  # noqa: BLE001
        pass
    resp = jsonify({'constellations': constellations, 'sats': sats,
                    'total_real': total, 'rendered': len(sats), 'source': 'celestrak'})
    # si alguna constelación falló, el resultado parcial no se guarda 24 h
    return _degraded(resp) if any(c.get('error') for c in constellations) else resp


def _fallback_tle():
    """Datos sintéticos cuando CelesTrak no es alcanzable — la demo nunca queda vacía."""
    import math
    groups = [('Starlink', 'SpaceX', '#ff7a45', 7134, 550, 53.0),
              ('OneWeb', 'EutelsatOneWeb', '#36cfc9', 648, 1200, 87.9),
              ('Planet Labs', 'PlanetLabs', '#73d13d', 200, 475, 97.4),
              ('Iridium NEXT', 'Iridium', '#40a9ff', 75, 780, 86.4),
              ('GPS', None, '#bfbfbf', 31, 20180, 55.0)]
    constellations, sats = [], []
    for idx, (label, node, color, real, alt_km, inc) in enumerate(groups):
        rendered = min(real, 200 if label == 'Starlink' else 80)
        constellations.append({'name': label, 'count': real, 'rendered': rendered,
                               'node': node, 'color': color})
        # genera líneas TLE plausibles distribuyendo RAAN/anomalía
        for k in range(rendered):
            raan = (360.0 * k / rendered) % 360
            ma = (137.5 * k) % 360
            mm = 86400.0 / (2 * math.pi * math.sqrt(((6371 + alt_km) * 1000) ** 3 / 3.986e14))
            l1 = f'1 {10000 + idx * 1000 + k:05d}U 24001A   24001.00000000  .00000000  00000-0  00000-0 0  9990'
            l2 = (f'2 {10000 + idx * 1000 + k:05d} {inc:8.4f} {raan:8.4f} 0001000 '
                  f'  0.0000 {ma:8.4f} {mm:11.8f}00000')
            sats.append({'n': f'{label}-{k}', 'l1': l1, 'l2': l2, 'c': idx})
    return {'constellations': constellations, 'sats': sats,
            'total_real': sum(c['count'] for c in constellations),
            'rendered': len(sats), 'source': 'fallback'}


# Pisos de respaldo por constelación (aprox. 2026): si CelesTrak falla en un
# grupo concreto (rate-limit), usamos este mínimo para que Starlink NO quede en 0
# ni "desaparezca" del resumen de texto.
_SAT_FALLBACK = {'Starlink': 8000, 'OneWeb': 648, 'Planet Labs': 190, 'Spire Global': 70,
                 'Iridium NEXT': 80, 'Globalstar': 28, 'SES / O3b': 68, 'GPS': 31,
                 'Galileo': 30, 'BeiDou': 50, 'Estaciones (ISS/CSS)': 20}


def _space_constellations():
    """[(label, count), …] satélites reales por constelación (CelesTrak), cacheado
    24h. Robusto: si un grupo falla usa su piso de respaldo (así Starlink nunca
    queda en 0). Compartido por el Khipu de TEXTO (/api/ai/command)."""
    ck = 'space_constellations'
    hit = cache.get(ck)
    if hit is not None:
        # tolera entradas viejas (label, n) cacheadas antes del flag "en vivo"
        return [tuple(x) if len(x) == 3 else (x[0], x[1], True) for x in hit]
    out = []
    for group, label, node, color in _SAT_GROUPS:
        try:
            r = requests.get(f'https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle',
                             timeout=10, headers={'User-Agent': 'KhipuFinance/1.0'})
            n = len(_parse_tle_text(r.text)) if (r.ok and r.text and '<' not in r.text[:1]) else 0
        except Exception:  # noqa: BLE001
            n = 0
        live = bool(n)
        if not n:
            n = _SAT_FALLBACK.get(label, 0)   # piso si CelesTrak falló para este grupo
        if n:
            out.append((label, n, live))      # live=False → cifra de REFERENCIA, no en vivo
    total = sum(n for _, n, _l in out)
    # cachear SOLO si el paquete es plausible (Starlink presente): evita fijar 24h
    # un resultado parcial como el que rompió el texto ("total 1163, sin Starlink").
    if total > 5000 and any(l == 'Starlink' and lv for l, _, lv in out):
        cache.set(ck, out, timeout=86400)
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
        out, model = _claude_complete(system, prompt, max_tokens=1400)
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


# ── Grafo de Conocimiento Temporal — /api/grafo/* ────────────────────────────
# El panel funciona 100% en el cliente (deriva hechos de NODES/LINKS/PREIPO).
# Estos endpoints añaden persistencia/ingesta y el upgrade opcional a Graphiti+Neo4j.
_neo4j_estado_cache = {'ok': None, 'ts': 0, 'err': None}


@app.route('/api/grafo/estado')
def grafo_estado():
    mode = _temporal_mode()
    connected = False
    err = None
    if mode == 'neo4j':
        # cache asimétrico: éxito 60s (no pingar Aura en cada apertura), fallo 8s
        # (para que el badge se recupere pronto tras un cold-start de Aura, sin
        # quedar rojo 60s). verify_connectivity tiene timeout corto (ver driver).
        c = _neo4j_estado_cache
        ttl = 60 if c['ok'] else 8
        if c['ok'] is not None and (time.time() - c['ts']) < ttl:
            connected, err = c['ok'], c['err']
        else:
            try:
                drv = _get_neo4j_driver()          # reusa el singleton
                drv.verify_connectivity()
                connected, err = True, None
            except Exception as e:  # noqa: BLE001
                connected = False
                err = _diag_redact(e)
            c['ok'], c['ts'], c['err'] = connected, time.time(), err
    payload = {'store': mode, 'neo4j_connected': connected}
    if not connected and mode == 'neo4j' and err:
        payload['error'] = err            # el badge/diag puede mostrar el porqué
    elif mode == 'native' and (NEO4J_URI or NEO4J_PASSWORD):
        # el usuario puso alguna var pero no todas / falta el driver
        payload['hint'] = ('NEO4J incompleto: revisa que NEO4J_URI, NEO4J_USER y '
                           'NEO4J_PASSWORD estén las 3 puestas y que el deploy incluya el driver neo4j.')
    # Metadatos SEGUROS para depurar el Unauthorized (nada de contraseña).
    if NEO4J_URI or NEO4J_PASSWORD:
        host = ''
        try:
            host = NEO4J_URI.split('://', 1)[-1].split('@')[-1].split('/')[0]
        except Exception:  # noqa: BLE001
            host = '(uri inválida)'
        payload['diag'] = {
            'user': NEO4J_USER,
            'uri_host': host,
            'uri_scheme': (NEO4J_URI.split('://', 1)[0] if '://' in NEO4J_URI else '(sin esquema)'),
            'pw_len': len(NEO4J_PASSWORD),
            'pw_had_spaces': _NEO4J_PASSWORD_RAW != _NEO4J_PASSWORD_RAW.strip(),
            'uri_had_spaces': _NEO4J_URI_RAW != _NEO4J_URI_RAW.strip(),
            'user_had_spaces': _NEO4J_USER_RAW != _NEO4J_USER_RAW.strip(),
        }
    return jsonify(payload)


@app.route('/api/grafo/seed', methods=['POST'])
@rate_limit(limit=20, window=3600)
def grafo_seed():
    """Carga masiva de hechos (el cliente empuja su catálogo derivado una vez
    cuando detecta Neo4j). Idempotente: MERGE por id, no duplica."""
    if _temporal_mode() != 'neo4j':
        return jsonify({'error': 'neo4j no configurado', 'store': 'native'}), 400
    b = request.get_json(force=True, silent=True) or {}
    facts = b.get('facts') or []
    if not isinstance(facts, list):
        return jsonify({'error': 'facts debe ser una lista'}), 400
    ok, fail = 0, 0
    for f in facts[:1000]:
        if not isinstance(f, dict) or not f.get('subject') or not f.get('id'):
            fail += 1
            continue
        try:
            _neo4j_add_fact(f)
            ok += 1
        except Exception:  # noqa: BLE001
            fail += 1
    return jsonify({'status': 'ok', 'persisted': ok, 'failed': fail, 'store': 'neo4j'})


_neo4j_driver = None
_neo4j_ready = False


def _get_neo4j_driver():
    """Driver singleton + constraints creadas una sola vez (idempotente)."""
    global _neo4j_driver, _neo4j_ready
    if _neo4j_driver is None:
        from neo4j import GraphDatabase
        # timeouts cortos: si Aura está dormida/caída, verify_connectivity falla
        # rápido en vez de colgar los 2 workers de gunicorn ~30s.
        _neo4j_driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD),
            max_connection_lifetime=600,
            connection_timeout=5,
            connection_acquisition_timeout=10,
            max_transaction_retry_time=8)
    if not _neo4j_ready:
        try:
            with _neo4j_driver.session() as s:
                s.run('CREATE CONSTRAINT khipu_entity_id IF NOT EXISTS '
                      'FOR (e:Entity) REQUIRE e.id IS UNIQUE')
                s.run('CREATE CONSTRAINT khipu_fact_id IF NOT EXISTS '
                      'FOR (f:Fact) REQUIRE f.id IS UNIQUE')
            _neo4j_ready = True
        except Exception:  # noqa: BLE001
            pass  # sin constraints igual funciona (MERGE deduplica de todos modos)
    return _neo4j_driver


# Cypher: un hecho = un nodo Fact colgado del sujeto; si el objeto es entidad,
# también lo enlaza. Guarda la ventana de validez (valid_from → valid_until).
_FACT_CYPHER = """
MERGE (s:Entity {id:$subject})
  ON CREATE SET s.label=$subject_label
  ON MATCH  SET s.label=coalesce(s.label,$subject_label)
MERGE (f:Fact {id:$fact_id})
  SET f.subject=$subject, f.predicate=$predicate, f.object=$object,
      f.object_type=$object_type, f.valid_from=$valid_from, f.valid_until=$valid_until,
      f.source=$source, f.confidence=$confidence, f.group=$group,
      f.headline=$headline
MERGE (s)-[:ASSERTS]->(f)
WITH f
FOREACH (_ IN CASE WHEN $is_edge THEN [1] ELSE [] END |
  MERGE (o:Entity {id:$object})
    ON CREATE SET o.label=$object_label
  MERGE (f)-[:ABOUT]->(o)
)
"""


def _neo4j_add_fact(fact):
    """Persiste un hecho temporal directamente en Neo4j (idempotente)."""
    drv = _get_neo4j_driver()
    NB = None  # el server no tiene el catálogo JS; usamos el id como label si no hay
    is_edge = fact.get('object_type') == 'node' and bool(fact.get('object'))
    params = {
        'subject': fact['subject'], 'subject_label': fact.get('subject_label') or fact['subject'],
        'fact_id': fact['id'], 'predicate': fact.get('predicate', ''),
        'object': fact.get('object', ''), 'object_type': fact.get('object_type', 'literal'),
        'object_label': fact.get('object_label') or fact.get('object', ''),
        'valid_from': fact.get('valid_from'), 'valid_until': fact.get('valid_until'),
        'source': fact.get('source', 'ingest'), 'confidence': float(fact.get('confidence') or 0.8),
        'group': fact.get('group', 'g_ingest'),
        'headline': (fact.get('meta') or {}).get('headline', ''),
        'is_edge': is_edge,
    }
    with drv.session() as s:
        s.run(_FACT_CYPHER, **params)


# ── Khipu voice — system prompt for ElevenLabs agent configuration ──────────
BIXBY_SYSTEM_PROMPT = """You are Khipu, the AI analyst co-pilot for Khipus Finance AI — a Bloomberg + Palantir-style platform for the global semiconductor, AI, space, energy and nuclear supply chain covering hundreds of curated companies and their typed relations (9 relation types) modeled as numeric matrices. You are a full investment analyst. You can open the X-Ray of any company, run LIVE shock/boom simulations on the map, compare two companies, surface opportunities, draw charts, and read the matrix chokepoints — all by silently calling your client tools.

## GOLDEN RULES OF SPEECH (CRITICAL — NEVER BREAK THESE)
- You act by CALLING YOUR CLIENT TOOLS. Tools are silent and instant.
- NEVER say, spell, read aloud or mention any command, token, tool name, bracket, code or internal id. The user must never hear anything technical — no "open_xray", no "[XRAY:...]", no "puedes escribir TSMC XRAY". Nothing of the sort, ever.
- NEVER tell the user to type a command, press a key or click a button to get something — just DO it yourself with your tools and narrate the RESULT naturally.
- Speak like a sharp human analyst: "Aquí tienes la radiografía de Nvidia — su mayor riesgo es la dependencia de TSMC…". Never like a machine.
- Company names: pass them to tools as plain names or tickers (e.g. "Nvidia", "NVDA", "TSMC") — the app resolves them, any casing works (it even fixes voice-transcription typos like "en vidia").
- If a tool returns {success:false} with an "error" text and/or "did_you_mean" suggestions, read that error text to the user AS-IS (it is already in the user's language, with no technical tokens) and offer the suggested companies naturally.

## TURN-TAKING / PATIENCE (IMPORTANT)
- When an action, analysis or lookup takes a few seconds, briefly say "dame un momento, lo estoy preparando" and then WAIT calmly for it.
- NEVER threaten to disconnect, and NEVER pressure the user about their silence. The user staying quiet while waiting for a result is completely normal — do NOT say things like "si no me respondes me desconecto". Just keep the conversation open patiently.
- Keep spoken replies short and to the point.

## APP STRUCTURE — 4 PRIMARY TABS (2026-07 redesign, NEXUS skin)
The 10 old panels are now grouped under 4 primary tabs. Underneath, switch_tab still targets the old tab ids (map, market, analysis, geo, simulation, space, terminal, canvas, tkg, guia, crypto).
1. 🗺️ MAPA — the unified graph. Nodes coloured by 9 MACRO-SECTORS (toggle to 40 categories in the legend). Sub-modes: Cadena (map) · Geopolítica (geo) · Espacio (space) · Grafo Temporal (tkg) · Simulación (simulation). Map controls: "◱ Capas" (toggle layers: links, labels, risk rings, marks, countries) and "◉ En vivo" (LIVE simulation panel — see below).
2. 📈 MERCADO — live prices, portfolio, P&L. Sub-mode ₿ Cripto (switch_tab 'crypto'): top-100 crypto market live (CoinGecko) + the curated "Expediente Khipus" dossier of the top 50 (what it is, mechanism, tokenomics, catalysts, risks, positioning, warning badges on politically-exposed or concentrated assets).
3. 💡 INSIGHTS — the "brain": auto-insight cards (chokepoints, risk, OPPORTUNITIES, sector panorama), the 9 relation MATRICES (heatmaps), topology metrics. Sub-modes: Análisis · Canvas IA · Terminal.
4. ❓ GUÍA — help.

## KEY FEATURES YOU CAN GUIDE THE USER TO
- 🔬 X-RAY (button on any company sheet): disassembles a company — NRS term by term, dependency threads, and the IMPACT WAVE (who suffers ↓ and who WINS ↑ if it falls, capital exposed). Powered by the matrix engine.
- ◉ LIVE SIMULATION (map): pick a shock TYPE (Corte↓ collapse, Demanda↑ boom, Precio, Sanción) and a TARGET (a preset, a whole sector, a whole country, or companies you pick) and drag severity — the map recolours in real time (red=harm, green=boom), with $ exposed, winners, sector breakdown and a replayable cascade. Simulations can be saved with date.
- ⇄ COMPARE two companies side by side.
- ☀️ BRIEF: the daily intelligence summary shown on open.

## YOUR TOOLS — when to call each (silently; results come back to you as data)
Analysis superpowers (prefer these — they are the platform's wow):
- open_xray(company_name): the user asks ANYTHING deep about one company — "desármame X", "why is X risky", "what depends on X", "analyze X". Opens the full X-Ray dossier on screen. Then narrate the 2-3 most interesting findings.
- run_live_simulation(company_name, kind, severity): "what if X falls / is sanctioned / booms". kind = collapse | demand | price | sanction. Returns affected count + most impacted; the screen shows the full wave. Narrate: how many companies, who suffers most, who WINS.
- compare_companies(company_a, company_b): "compare X and Y". Returns both NRS + which has lower risk. Screen shows them side by side.
- get_opportunities(): "where do I invest", "opportunities". Returns resilient companies (low risk + growth + margin).
- create_visualization(query): the user asks to chart / graph / tabulate ANYTHING — pass a natural-language description (e.g. "márgenes de Nvidia, TSMC y ASML") and it renders automatically.
- show_insights(): opens the insights brain + the 9 relation matrices.
- run_stress_test(ticker): classic failure cascade on the map.
- run_simulation(scenario_id): war-room presets: taiwan_conflict, china_chip_ban_total, hbm_shortage_2027, openai_ipo_impact, starshield_reveal.
- run_agent_simulation(scenario, companies): a MULTI-AGENT simulation — several analyst agents debate a scenario and project REALISTIC impacts on the supply chain. Use for open-ended "simula / qué pasaría si…" questions that benefit from a debate. The full sim appears on screen; narrate the consensus, the biggest impacts, and where agents disagreed.
- deep_research(company): a DEEP investigation that goes BEYOND one company — sector panorama, direct competitors, geopolitical exposure, supply-chain chokepoints and an investment thesis. Use when the user wants a thorough dossier, not a quick fact; it appears on screen in a few seconds.

Data lookups:
- get_company_info(company_name) · get_risk_score(company_name) · get_news(company_name)
- get_market_summary() · get_portfolio_risk() · list_companies(category, limit) · get_supply_chain_links(company_name)

Navigation & UI:
- navigate_to_company(company_name) · switch_tab(tab: map|market|analysis|geo|simulation|space|terminal|canvas|tkg|guia|crypto)
- show_chart(ticker) · open_terminal(ticker) · place_trade(ticker) · open_second_brain(company_name) · open_cockpit()

Paper trading (SIMULATED broker — strict rules in PAPER TRADING section below):
- place_paper_trade(symbol_or_name, side, notional_usd, confirmed) · get_portfolio_status()
- open_dossier(company_name): the FINANCIAL DOSSIER card (revenue growth, dilution, FCF, stock, EV/Sales, debt, margins, ROE). Use when the user asks for "fundamentales", "dossier", or a financial overview of one listed company.
When the full-screen cockpit is open, the graph and the terminal render INSIDE it automatically — navigate_to_company and open_terminal show them on the cockpit stage, never in a hidden tab.

You may receive [CONTEXT_UPDATE] {json} messages — silent app-state snapshots (selected company, portfolio, top risks). Use them to be sharper; never read them aloud or acknowledge them.

## DOMAIN KNOWLEDGE — DEEP EXPERTISE

NRS (NEXUS Risk Score): 0-100, HIGHER = RISKIER. Sum of: country geo-risk (0-30), supply-chain centrality (0-25, from graph degree), margin-based market risk (0-20), fundamentals (0-15: pre-IPO, weak growth), country concentration (0-10). >70=HIGH (red), 40-70=MEDIUM (yellow), <40=LOW (green). For a company's actual NRS use the app's tools/context — never quote an NRS from memory.

Critical chokepoints (structural roles; for scores, prices or market caps use the app's live data, never memory):
- TSMC: leading advanced foundry; Apple/NVIDIA/AMD/Qualcomm depend on it.
- ASML: EUV lithography monopoly; no leading-edge nodes without them.
- NVIDIA: dominant AI training GPU supplier.
- SK Hynix: leading HBM supplier for AI accelerators.
- Arm: CPU ISA licensed across mobile and many data-center chips.
- Synopsys/Cadence: EDA duopoly; needed to design modern chips.

Supply chains (know the full stack):
- AI data center: NVIDIA GPU → TSMC fab → ASML litho → SK Hynix HBM → Broadcom switch
- Smartphone: Apple/Qualcomm SoC → TSMC fab → ARM ISA → Sony camera → Samsung display
- Space: SpaceX Falcon/Starship → Rocket Lab Electron → Maxar/Planet satellites → Iridium comms
- Automotive AI: NXP/Renesas SoC → STMicro power → Mobileye vision → LiDAR (Luminar)
- Quantum: IBM/IonQ/Rigetti systems → Oxford Instruments cryo → Keysight control

Geopolitical risks (qualitative; quote numbers only from live data or sourced context):
- Taiwan Strait: most leading-edge fab capacity (TSMC, UMC, ASE) is concentrated there. Conflict → global chip shortage
- US-China: export controls on advanced AI GPUs to China; Huawei building an alternative stack (Ascend)
- Rare earths: China dominates supply and processing; MP Materials/Lynas are US/AU alternatives
- Korea: Samsung + SK Hynix concentrate most DRAM/HBM supply

War-Room scenarios (5 presets; HYPOTHETICAL — outcomes come from running the simulation, never from memory):
1. taiwan_conflict — TSMC blockade and its cascade
2. china_chip_ban_total — total US chip export ban to China
3. hbm_shortage_2027 — HBM memory shortage
4. openai_ipo_impact — OpenAI IPO and the AI ecosystem
5. starshield_reveal — SpaceX Starshield defense program

## PAPER TRADING (SIMULATED — RULES YOU MUST NEVER BREAK)
- place_paper_trade and get_portfolio_status operate on a SIMULATED paper-money broker. ALWAYS say clearly that the operation is simulated ("es una operación simulada, dinero de papel") — never let the user believe real money moved.
- NEVER execute a trade without explicit verbal confirmation. The flow is ALWAYS two steps: (1) call place_paper_trade with confirmed=false — it returns an order summary WITHOUT executing; read that summary to the user (symbol, buy/sell, USD amount, simulated) and ask if they confirm. (2) ONLY after the user explicitly says yes ("sí", "confirmo", "dale", "yes"), call place_paper_trade again with the SAME parameters and confirmed=true. Silence, hesitation or an ambiguous answer is NOT a yes — ask again or drop it.
- Around a TRADE you execute exactly what the user asked and report the result — you never push them to trade. If they ask what to buy you may give a CAUTIOUS stance (see below), never a blunt "buy/sell", always noting it is analysis, not formal financial advice, and the decision is theirs.
- If the tool returns an error message, read it to the user AS-IS (it is already user-friendly, in their language) and do NOT retry on your own.
- Amounts are in US dollars (notional): minimum $1, maximum $100,000 per order.

## ANALYST BEHAVIOR RULES
- For ANY question that needs facts or analysis, call ask_khipu_brain FIRST and answer from what it returns (it has live data and sources); only answer from your own knowledge for pure definitions or small talk.
- You are a financial analyst first, voice assistant second. Give real insight, not just navigation.
- ACT FIRST, TALK SECOND: on almost every user request, call the right tool immediately, then narrate what appeared on screen with 1-3 sentences of real insight. Never just speak without acting, and never ask permission to act.
- Deep question about ONE company → open_xray + your sharpest take ("Su talón de Aquiles es…").
- "What if…" questions → run_live_simulation, then narrate: how many affected, the 2-3 biggest victims, who wins.
- War-room narration: describe the cascade ("TSMC absorbe el primer golpe, luego caen los fabless…") and name winners and losers USING THE % THE SIMULATION RETURNED — always say they are simulated estimates of a hypothetical scenario, never real prices.
- Charts: create_visualization — never ask the user to describe the chart format, just render something smart.
- Confirm actions naturally and briefly: "Aquí la tienes…", "Mira el mapa — se tiñe en rojo…".
- Be concise (2-3 sentences of analysis) then act immediately — no over-explanation.
- Match user language exactly (Spanish/English/mixed — follow their lead). Default to Spanish.
- When asked investment questions, give a CAUTIOUS take WITH A STANCE — you may lean ("me inclinaría por… / sería cauto con TSMC porque…"), name the 2-3 key factors and a confidence level (alta/media/baja), but NEVER a blunt "compra/vende". ALWAYS close with a short reminder that this is analysis, not formal financial advice, and the decision is theirs. This soft-stance rule applies to stocks AND crypto.
- You can run MULTI-AGENT simulations from your own terminal (run_agent_simulation): several analyst agents debate a scenario and project realistic impacts. Reach for them on open-ended "¿qué pasaría si…? / what would happen if…" questions where a debate adds value.
- You are a Bloomberg Terminal AI co-pilot for serious investors, not a general chatbot"""


# ── Khipu — client tools registradas en el agente de ElevenLabs vía API ──────
# Cada entrada espeja un `case` de _handleToolCall en engine/voice.js.
# El agente las llama en silencio (el usuario nunca oye nombres de herramientas).
def _bixby_client_tools():
    def T(name, desc, props=None, required=None):
        return {
            'type': 'client', 'name': name, 'description': desc,
            'expects_response': True,
            'parameters': {'type': 'object',
                           'properties': props or {},
                           'required': required or []},
        }
    S = lambda d: {'type': 'string', 'description': d}  # noqa: E731
    N = lambda d: {'type': 'number', 'description': d}  # noqa: E731
    company = {'company_name': S('Company name or ticker, any casing (e.g. "Nvidia", "NVDA", "tsmc")')}
    return [
        T('ask_khipu_brain', 'THE DEFAULT TOOL FOR ANY QUESTION. Sends the user question to the Khipus analyst brain, which LOOKS UP real data in the app (company profiles, supply chain, live prices and news, AI research conclusions, portfolio risk, geopolitical and space events, committee memos, track record) and returns a sourced answer. Use it for every analysis/knowledge question ("what are TSMC risks?", "what happened with Nvidia today?", "which companies are most critical?", follow-ups). Read the returned answer aloud naturally and briefly (summarize long lists); never contradict its figures with your own memory. It is read-only: it never places orders.', {'question': S('The user question, in their own words, including enough context for follow-ups (e.g. "and who depends on TSMC?").')}, ['question']),
        T('open_xray', 'Open the full X-Ray dossier of a company (NRS breakdown, dependency threads, impact wave: who suffers and who wins if it falls). Use for ANY deep question about one company.', company, ['company_name']),
        T('run_live_simulation', 'Run a live shock/boom simulation on the supply-chain map. Returns affected count and most impacted companies.', dict(company, kind=S('collapse | demand | price | sanction (default collapse)'), severity=N('0-100, default 100')), ['company_name']),
        T('compare_companies', 'Compare two companies side by side. Returns NRS of each and which has lower risk.', {'company_a': S('First company name/ticker'), 'company_b': S('Second company name/ticker')}, ['company_a', 'company_b']),
        T('get_opportunities', 'Resilient companies with upside: low risk + growth + healthy margin.'),
        T('create_visualization', 'Render a chart/table from a natural-language description of what to visualize.', {'query': S('What to chart, in natural language (e.g. "márgenes de Nvidia, TSMC y ASML")')}, ['query']),
        T('show_insights', 'Show what the HYPERGRAPH sees: it runs a LIVE simulation over the active systemic factors (hyperedges) and the supply-chain cascade, then returns narrated insights + the most-affected companies. Use for "¿qué ves en el grafo?", "dame insights", "qué factores hay activos", "qué está en riesgo en el sistema". Narrate 2-3 of the returned insights, naming companies; it is analysis, not advice.'),
        T('run_guided_demo', 'Start the GUIDED DEMO (full app tour, narrated on screen). STRICT RULE: call this ONLY when the user EXPLICITLY asks for a demo or tour with words like "demo", "demostración", "tour", "recorrido", "hazme una demo". NEVER call it at session start, NEVER on greetings, NEVER because the user seems new, NEVER proactively — an unwanted tour interrupts the user. After calling it, say ONE short line and STAY QUIET.'),
        T('run_stress_test', 'Run the classic failure-cascade stress test from one company on the map.', {'ticker': S('Ticker or company name')}, ['ticker']),
        T('run_simulation', 'Launch a war-room scenario preset.', {'scenario_id': S('taiwan_conflict | china_chip_ban_total | hbm_shortage_2027 | openai_ipo_impact | starshield_reveal')}, ['scenario_id']),
        T('run_agent_simulation', 'Run a MULTI-AGENT simulation: several analyst agents debate a scenario and project REALISTIC impacts on the supply chain. Use for open-ended "simula / what if…" questions where a debate adds value. The full simulation appears on screen.', {
            'scenario': S('The scenario in natural language, e.g. "China prohíbe exportar HBM"'),
            'companies': {'type': 'array',
                          'items': {'type': 'string', 'description': 'A company name or ticker'},
                          'description': 'Seed companies/tickers to center the simulation on (optional, any casing)'},
        }, ['scenario']),
        T('deep_research', 'Run a DEEP research investigation that goes BEYOND one company — sector panorama, direct competitors, geopolitical exposure, supply-chain chokepoints and an investment thesis. Use when the user wants a thorough dossier, not a quick fact. Appears on screen; takes a few seconds.', {'company': S('Company name or ticker, any casing')}, ['company']),
        T('get_company_info', 'EVERYTHING the app knows about one company: live price, NRS risk, sector, country, EMPLOYEES, FOUNDED year, REVENUE, market cap, margin, growth, moat, geo risk, description, supplier/customer counts. ALWAYS call this before saying you do not know a fact about a company.', company, ['company_name']),
        T('get_risk_score', 'NRS risk score (0-100) of a company with breakdown.', company, ['company_name']),
        T('get_news', 'Recent news with sentiment for a company.', company, ['company_name']),
        T('get_market_summary', 'All current market prices with % change.'),
        T('get_portfolio_risk', 'VaR/CVaR risk of the user portfolio.'),
        T('list_companies', 'List companies, optionally by category.', {'category': S('Category filter (optional)'), 'limit': N('Max results (default 10)')}),
        T('get_supply_chain_links', 'Upstream/downstream supply-chain connections of a company.', company, ['company_name']),
        T('navigate_to_company', 'Jump to a company on the map.', company, ['company_name']),
        T('switch_tab', 'Switch app tab. Use tab="crypto" for the live crypto market + Expediente dossier — it opens INSIDE the Khipu cockpit (does not close it).', {'tab': S('map | market | analysis | geo | simulation | space | terminal | canvas | tkg | guia | crypto')}, ['tab']),
        T('show_chart', 'Show the stock chart of a ticker in the side panel.', {'ticker': S('Ticker')}, ['ticker']),
        T('open_terminal', 'Open the multi-chart Bloomberg-style terminal on a ticker.', {'ticker': S('Ticker')}, ['ticker']),
        T('place_trade', 'Open the buy/sell trade modal for a ticker (the user confirms manually).', {'ticker': S('Ticker')}, ['ticker']),
        T('open_second_brain', 'Open the AI intelligence panel for a company.', company, ['company_name']),
        T('open_cockpit', 'Open the full-screen Khipu cockpit view.'),
        T('deep_analysis', 'Run a multi-step DEEP investigation (plan → context → simulation → synthesis) for a complex investment question. Takes 30-90 seconds; the full analysis appears on screen — tell the user you are investigating and it will appear shortly.', {'question': S('The complete question, in the user language')}, ['question']),
        T('open_dossier', 'Open the FINANCIAL DOSSIER card of a listed company: revenue growth, dilution, free cash flow, stock, EV/Sales valuation, debt/equity, margins and ROE (investingvisuals-style small multiples).', company, ['company_name']),
        T('place_paper_trade', 'Execute a SIMULATED (paper-money) buy/sell order on the paper broker — never real money. MUST be called FIRST with confirmed=false: it returns an order summary WITHOUT executing; read that summary to the user and ask for confirmation. ONLY after an explicit verbal yes, call again with the same parameters and confirmed=true to execute. Never give investment advice; if the tool returns an error, read it as-is.', {
            'symbol_or_name': S('Ticker, crypto pair or company/asset name, any casing (e.g. "NVDA", "Nvidia", "BTC/USD", "bitcoin")'),
            'side': S('buy | sell'),
            'notional_usd': N('Amount in US dollars (e.g. 100 = $100). Min 1, max 100000.'),
            'confirmed': {'type': 'boolean', 'description': 'false = preview only (returns the summary to read to the user). true = EXECUTE — only allowed after the user explicitly said yes to the summary.'},
        }, ['symbol_or_name', 'side', 'notional_usd', 'confirmed']),
        T('get_portfolio_status', 'Status of the SIMULATED paper-broker account: cash, equity, buying power and all open positions with P&L. Use when the user asks about their paper portfolio, balance or positions.'),
        T('get_space_summary', 'REAL satellite counts per constellation (Starlink, OneWeb, Planet Labs, Iridium, GPS) from CelesTrak, plus the next launch. Use WHENEVER the user asks how many satellites an operator/constellation has, or anything about satellites, space or launches. Read the returned summary and counts to the user — never say you do not know, this tool has the real number.', {'query': S('Optional operator/constellation the user asked about, e.g. "Starlink", "OneWeb". Leave empty for the overall summary.')}),
    ]


def _sync_bixby_agent():
    """Empuja el cerebro de Khipu (system prompt + client tools + idioma) al
    agente de ElevenLabs vía PATCH — así Fabrizio no configura nada a mano.
    Idempotente; si el esquema de tools no es aceptado, reintenta solo-prompt.

    OJO (bug real 2026-07): ElevenLabs exige que los agentes NO-ingleses usen
    un modelo TTS turbo/flash v2.5 — si el agente quedó en otro modelo, el
    PATCH con language='es' devuelve 400. Por eso: leemos la config actual,
    PRESERVAMOS la voz elegida y solo corregimos el model_id si hace falta."""
    if not (ELEVENLABS_KEY and ELEVENLABS_AGENT_ID):
        return {'ok': False, 'error': 'ELEVENLABS_KEY / ELEVENLABS_AGENT_ID no configurados'}
    url = f'https://api.elevenlabs.io/v1/convai/agents/{ELEVENLABS_AGENT_ID}'
    hdrs = {'xi-api-key': ELEVENLABS_KEY, 'Content-Type': 'application/json'}

    # 1) leer config actual para preservar voz y decidir el modelo TTS
    tts_patch = None
    try:
        cur = requests.get(url, headers={'xi-api-key': ELEVENLABS_KEY}, timeout=15).json()
        cur_tts = ((cur.get('conversation_config') or {}).get('tts') or {})
        model = str(cur_tts.get('model_id') or '')
        if 'v2_5' not in model and 'v3' not in model:
            # modelo incompatible con agentes en español → flash v2.5 (baja latencia)
            tts_patch = {'model_id': 'eleven_flash_v2_5'}
            if cur_tts.get('voice_id'):
                tts_patch['voice_id'] = cur_tts['voice_id']   # conservar SU voz
    except Exception:  # noqa: BLE001
        tts_patch = {'model_id': 'eleven_flash_v2_5'}

    def _payload(with_tools):
        agent_cfg = {'prompt': {'prompt': BIXBY_SYSTEM_PROMPT}, 'language': 'es'}
        if with_tools:
            agent_cfg['prompt']['tools'] = _bixby_client_tools()
        cc = {'agent': agent_cfg}
        if tts_patch:
            cc['tts'] = tts_patch
        return {'conversation_config': cc}

    try:
        r = requests.patch(url, json=_payload(True), headers=hdrs, timeout=25)
        if r.status_code < 400:
            # verificación: ¿cuántas tools quedaron registradas?
            n_tools = None
            try:
                chk = requests.get(url, headers={'xi-api-key': ELEVENLABS_KEY}, timeout=15).json()
                n_tools = len((((chk.get('conversation_config') or {}).get('agent') or {})
                               .get('prompt') or {}).get('tools') or [])
            except Exception:  # noqa: BLE001
                pass
            return {'ok': True, 'mode': 'full', 'status': r.status_code, 'tools_registered': n_tools,
                    'tts_fixed': bool(tts_patch)}
        # fallback: algunos planes/versiones del API rechazan tools inline
        detail = (r.text or '')[:400]
        r2 = requests.patch(url, json=_payload(False), headers=hdrs, timeout=25)
        return {'ok': r2.status_code < 400, 'mode': 'prompt_only', 'status': r2.status_code,
                'tools_error': detail, 'prompt_error': None if r2.status_code < 400 else (r2.text or '')[:400]}
    except Exception as e:  # noqa: BLE001
        return {'ok': False, 'error': str(e)[:300]}


@app.route('/api/voice/sync-agent', methods=['GET', 'POST'])
@rate_limit(limit=6, window=3600)
@_require_operator
def voice_sync_agent():
    """Sincroniza el agente de ElevenLabs con el cerebro definido aquí (PATCH
    del agente). PIN de operador: antes cualquiera podía dispararlo en bucle.
    El autosync del arranque no pasa por aquí."""
    res = _sync_bixby_agent()
    return jsonify(res), (200 if res.get('ok') else 502)


# Auto-sync al arrancar (BIXBY_AUTOSYNC=0 para desactivar). En background para
# no retrasar el boot; idempotente aunque los 2 workers de gunicorn lo llamen.
if os.getenv('BIXBY_AUTOSYNC', '1').strip().lower() not in ('0', 'false', 'no'):
    def _bixby_autosync():
        time.sleep(4)
        res = _sync_bixby_agent()
        if res.get('ok'):
            log.info('Khipu sincronizado con ElevenLabs (%s, tools=%s)', res.get('mode'), res.get('tools_registered'))
        else:
            log.warning('Khipu autosync falló (la app sigue): %s', res)
    try:
        if ELEVENLABS_KEY and ELEVENLABS_AGENT_ID:
            threading.Thread(target=_bixby_autosync, daemon=True).start()
    except Exception as _e:  # noqa: BLE001
        log.warning('Khipu autosync no arrancó: %s', _e)


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
            'Eres el analista jefe de Khipus Finance AI. Escribe en español, '
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
def client_diag_recent():
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

@app.route('/api/voice/bixby-prompt', methods=['GET'])
def bixby_system_prompt():
    """Returns Khipu's system prompt for ElevenLabs agent configuration."""
    # allow_override: set ELEVENLABS_ALLOW_OVERRIDE=true in Railway env vars ONLY
    # if your ElevenLabs agent dashboard has "Allow overrides" turned ON.
    # Sending a prompt override when overrides are OFF causes ElevenLabs to close
    # the WebSocket immediately.
    allow_override = os.getenv('ELEVENLABS_ALLOW_OVERRIDE', 'false').lower() == 'true'
    return jsonify({
        'system_prompt': BIXBY_SYSTEM_PROMPT,
        'agent_name': 'Khipu',
        'platform': 'Khipu Finance',
        'allow_override': allow_override,
    })


# ── Khipu voice — sesión firmada de ElevenLabs ───────────────────────────────
@app.route('/api/voice/session', methods=['POST'])
def voice_session():
    if not ELEVENLABS_KEY:
        return jsonify({'error': 'ELEVENLABS_KEY not configured'}), 400
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id') or ELEVENLABS_AGENT_ID
    if not agent_id:
        return jsonify({'error': 'agent_id required'}), 400
    try:
        r = requests.get(
            'https://api.elevenlabs.io/v1/convai/conversation/get_signed_url',
            params={'agent_id': agent_id},
            headers={'xi-api-key': ELEVENLABS_KEY}, timeout=10)
        return jsonify(r.json()), r.status_code
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200]}), 502


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


# ── /api/quotes/live — batch quotes with pct change ──────────────────────────
@app.route('/api/quotes/live', methods=['POST'])
@rate_limit(limit=60, window=60)
def quotes_live():
    """Batch live quotes with pct change. Body: {"tickers": ["NVDA","TSM",...]}.
    Tries Finnhub first, falls back to Yahoo Finance per ticker.
    Returns {ticker: {close, prev, live, pct, vol}}.
    """
    data = request.get_json(silent=True) or {}
    tickers = [s for s in (_safe_ticker(t) for t in (data.get('tickers') or [])) if s]
    tickers = tickers[:100]
    if not tickers:
        return jsonify({'error': 'tickers required'}), 400

    from core.quotes import fetch_quote_intl, is_intl
    results = {}
    for tk in tickers:
        q = None
        # 0) Bolsas no-EEUU (sufijo Yahoo): directo a Yahoo + conversión a USD
        if is_intl(tk):
            q = fetch_quote_intl(tk)
            if q:
                results[tk] = q
            continue
        # 1) Finnhub
        if FINNHUB:
            fh, err = _fetch_quote_raw(tk, timeout=4)
            if fh and fh.get('c') and fh.get('pc'):
                close = fh['c']
                prev  = fh['pc']
                live  = fh.get('c', close)
                pct   = (live - prev) / prev * 100 if prev else 0
                q = {'close': close, 'prev': prev, 'live': live, 'pct': round(pct, 3),
                     'vol': fh.get('v', 0)}
        # 2) Yahoo Finance fallback
        if q is None:
            try:
                yf_url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{tk}'
                          f'?interval=1d&range=5d')
                yf_r = requests.get(yf_url,
                                    headers={'User-Agent': 'Mozilla/5.0 (compatible; Khipu/1.0)'},
                                    timeout=6)
                if yf_r.status_code == 200:
                    ydata = yf_r.json()
                    result = ((ydata.get('chart') or {}).get('result') or [None])[0]
                    if result:
                        meta   = result.get('meta', {})
                        closes = (result.get('indicators', {}).get('quote', [{}])[0]
                                  .get('close', []))
                        closes = [c for c in closes if c is not None]
                        if len(closes) >= 2:
                            close = closes[-1]
                            prev  = closes[-2]
                            live  = meta.get('regularMarketPrice', close)
                            pct   = (live - prev) / prev * 100 if prev else 0
                            vol   = meta.get('regularMarketVolume', 0)
                            q = {'close': close, 'prev': prev, 'live': live,
                                 'pct': round(pct, 3), 'vol': vol}
            except Exception:  # noqa: BLE001
                pass
        if q:
            results[tk] = q

    return jsonify(results)


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


# ── AI Trading Agent ─────────────────────────────────────────────────────────
# Endurecimiento (auditoría estructural 2026-09-30, #11/#12/#21):
#  · parámetros ACOTADOS (max_pos_pct 0.5-10, max_daily_loss_pct 0.5-5,
#    stop_loss_pct 0.5-20, min_confidence 50-100, órdenes/ciclo 1-5,
#    intervalo 5-1440 min) y mode ∈ {manual, auto}; arranque bajo lock (sin
#    dos hilos a la vez);
#  · modo AUTO (órdenes sin aprobación por orden) SOLO en cuenta de PAPEL: con
#    dinero real se rechaza (403 'auto_live_refused') y el ciclo no envía nada;
#  · interruptor BROKERAGE_TRADING_ENABLED=off → el agente no envía órdenes;
#  · una orden que Alpaca RECHAZA (4xx/5xx) queda como ERROR, nunca como
#    ejecutada; cada intento va a broker_audit (o al log sin base);
#  · stop-loss cripto con time_in_force 'gtc' (Alpaca no acepta 'day' en
#    cripto) y sin reenviar el cierre si ya hay uno pendiente;
#  · universo saneado: solo acciones de EE.UU. operables en Alpaca (los
#    tickers extranjeros del grafo se descartan; ya no van crudos a la URL).

_AGENT: dict = {
    'running': False,
    'mode': 'manual',          # 'manual' | 'auto'
    'interval_min': 15,
    'universe': ['NVDA','TSM','AMD','INTC','ASML','AMAT','QCOM','AVGO','MU','TSLA'],
    'max_pos_pct': 5.0,        # max % of equity per position
    'max_daily_loss_pct': 2.0, # daily circuit-breaker
    'stop_loss_pct': 3.0,      # per-position stop
    'min_confidence': 65,      # umbral para ejecutar (antes hardcodeado)
    'max_orders_per_cycle': 3, # freno duro anti-loop: máx órdenes nuevas por ciclo
    'log': [],
    'thread': None,
    'last_run': None,
    'status': 'stopped',
    'daily_pnl_pct': 0.0,
    'broker_error': None,      # último error de Alpaca (bilingüe) para diagnóstico
    'pending_close': {},       # símbolo (sin '/') → ts del último cierre enviado
}
_AGENT_LOCK = threading.Lock()          # arranque/parada/config
_AGENT_LOG_LOCK = threading.Lock()
_AGENT_LOG_MAX = 100
_AGENT_PENDING_CLOSE_S = 1800           # no reenviar un stop-loss en 30 min
_AGENT_BOUNDS = {                        # clave → (mínimo, máximo, tipo)
    'max_pos_pct': (0.5, 10.0, float),
    'max_daily_loss_pct': (0.5, 5.0, float),
    'stop_loss_pct': (0.5, 20.0, float),
    'min_confidence': (50, 100, int),
    'max_orders_per_cycle': (1, 5, int),
    'interval_min': (5, 1440, int),
}
_AGENT_MODES = ('manual', 'auto')
# Acciones de EE.UU. operables en Alpaca: 1-5 letras + clase opcional (BRK.B).
# Deja fuera sufijos de bolsas extranjeras del grafo (8411.T, SAP.DE, 0700.HK…).
_AGENT_SYM_RE = re.compile(r'^[A-Z]{1,5}(\.[A-C])?$')
_TRADABLE_CACHE: dict = {}
_AGENT_CFG_KEYS = ('mode', 'interval_min', 'max_pos_pct', 'max_daily_loss_pct', 'stop_loss_pct',
                   'min_confidence', 'max_orders_per_cycle', 'universe')


class _AgentOrderError(RuntimeError):
    """Alpaca no aceptó la orden (o no respondió): NO cuenta como ejecutada."""


def _agent_log(entry):
    entry.setdefault('ts', time.strftime('%H:%M:%S'))
    with _AGENT_LOG_LOCK:
        _AGENT['log'].append(entry)
        if len(_AGENT['log']) > _AGENT_LOG_MAX:
            _AGENT['log'] = _AGENT['log'][-_AGENT_LOG_MAX:]


def _agent_universe(raw):
    """→ (símbolos operables, descartados). None si `raw` no es una lista."""
    if not isinstance(raw, (list, tuple)):
        return None, []
    ok, skipped = [], []
    for t in list(raw)[:60]:
        sym = _safe_ticker(t)
        if sym and _AGENT_SYM_RE.match(sym):
            if sym not in ok:
                ok.append(sym)
        else:
            skipped.append(str(t)[:16])
    return ok[:30], skipped


def _agent_parse(data):
    """Valida y ACOTA la configuración → (cambios, avisos, (error_es, error_en)|None)."""
    changes, notes = {}, []
    for k, (lo, hi, typ) in _AGENT_BOUNDS.items():
        if k not in data or data[k] is None or data[k] == '':
            continue
        try:
            v = float(data[k])
            if v != v or v in (float('inf'), float('-inf')):
                raise ValueError
        except (TypeError, ValueError):
            return None, None, (f'{k} debe ser numérico', f'{k} must be numeric')
        cv = min(hi, max(lo, v))
        cv = int(round(cv)) if typ is int else float(cv)
        if cv != v:
            notes.append(f'{k}: {data[k]} → {cv}')
        changes[k] = cv
    if data.get('mode') not in (None, ''):
        m = str(data['mode']).strip().lower()
        if m not in _AGENT_MODES:
            return None, None, ("mode debe ser 'manual' o 'auto'", "mode must be 'manual' or 'auto'")
        changes['mode'] = m
    if data.get('universe') not in (None, [], ''):
        uni, skipped = _agent_universe(data['universe'])
        if uni is None:
            return None, None, ('universe debe ser una lista de tickers', 'universe must be a list of tickers')
        if not uni:
            return None, None, ('Ningún ticker del universo es una acción de EE.UU. operable en Alpaca',
                                'No ticker in the universe is a US stock tradable on Alpaca')
        changes['universe'] = uni
        if skipped:
            notes.append('descartados (no operables en Alpaca) · skipped (not tradable on Alpaca): '
                         + ', '.join(skipped[:12]) + ('…' if len(skipped) > 12 else ''))
    return changes, notes, None


def _agent_config_view():
    return {k: _AGENT[k] for k in _AGENT_CFG_KEYS}


def _auto_live_refused():
    log.warning('agente de trading: modo AUTO rechazado — la cuenta de Alpaca es de DINERO REAL')
    _trade_audit('agent_config', {'outcome': 'rejected', 'reason': 'auto_live_refused'})
    return _bad('El modo AUTO (órdenes sin tu aprobación una a una) solo se permite en la cuenta de PAPEL. '
                'Con dinero real usa el modo manual (consejos) y opera tú.',
                'AUTO mode (orders without your one-by-one approval) is only allowed on the PAPER account. '
                'With real money use manual mode (advice) and place orders yourself.',
                code='auto_live_refused', status=403)


def _agent_exec_block(account=None):
    """None si el agente puede enviar órdenes ahora; si no, el motivo (bilingüe).
    `account` (/v2/account): si su account_number no es de papel ('PA…') se
    bloquea aunque la URL parezca de papel."""
    if not _house_trading_enabled():
        return ('Interruptor general APAGADO (BROKERAGE_TRADING_ENABLED=off) · '
                'Master switch OFF (BROKERAGE_TRADING_ENABLED=off)')
    if not _paper() or _account_is_live(account) is True:
        return 'Cuenta de DINERO REAL: el modo auto no envía órdenes · REAL-MONEY account: auto mode sends no orders'
    return None


def _agent_analyze(ticker: str, price: float, prev: float, sentiment: float) -> dict:
    """Ask Claude to analyze one ticker and recommend action."""
    pct = ((price - prev) / prev * 100) if prev else 0
    prompt = (
        f"You are a quantitative trading analyst. Analyze {ticker}:\n"
        f"- Price: ${price:.2f} (prev close: ${prev:.2f}, change: {pct:+.2f}%)\n"
        f"- News sentiment score: {sentiment:.2f} (range -10 to +10)\n\n"
        f"Respond in JSON only, no markdown:\n"
        f'{{ "action": "buy"|"sell"|"hold", "confidence": 0-100, '
        f'"reason": "1-sentence reason", "size_pct": 1-5 }}'
    )
    try:
        # Ruta a través de la cascada multi-proveedor (Sonnet 5 con pensamiento
        # desactivado → respuesta inmediata; _extract_json tolera fences/prosa).
        text, _model = _ai_complete(
            'You are a quantitative trading analyst. Respond with a JSON object ONLY, no markdown.',
            prompt, max_tokens=250, tier='fast')
        out = _extract_json(text)
        return out if isinstance(out, dict) else {'action': 'hold', 'confidence': 0,
                                                  'reason': 'respuesta no-JSON', 'size_pct': 0}
    except Exception as e:  # noqa: BLE001
        return {'action': 'hold', 'confidence': 0, 'reason': _diag_redact(e)[:80], 'size_pct': 0}


def _agent_clean_analysis(a):
    """La IA puede devolver cualquier cosa: se normaliza sin reventar el ciclo."""
    a = a if isinstance(a, dict) else {}
    action = str(a.get('action') or 'hold').strip().lower()
    if action not in ('buy', 'sell', 'hold'):
        action = 'hold'
    try:
        confidence = int(float(a.get('confidence') or 0))
    except (TypeError, ValueError):
        confidence = 0
    try:
        size_pct = float(a.get('size_pct') or 0)
        if size_pct != size_pct:
            size_pct = 0.0
    except (TypeError, ValueError):
        size_pct = 0.0
    return action, max(0, min(100, confidence)), str(a.get('reason') or '')[:200], \
        max(0.0, min(size_pct, float(_AGENT['max_pos_pct'])))


def _agent_get_positions() -> dict:
    if not ALPACA_KEY:
        return {}
    try:
        r = requests.get(f'{ALPACA_BASE}/v2/positions', headers=_alpaca_hdrs(), timeout=10)
        if r.status_code == 200:
            return {p['symbol']: p for p in r.json()}
    except Exception:  # noqa: BLE001
        pass
    return {}


def _agent_open_order_symbols():
    """{símbolo sin '/': {lados}} de las órdenes ABIERTAS en Alpaca; None si no
    se pudo leer. El LADO importa: una compra límite abierta (p. ej. 'comprar
    la caída' GTC) NO es un cierre pendiente de una posición larga — antes
    cualquier orden abierta del símbolo apagaba el stop-loss."""
    try:
        r = requests.get(f'{ALPACA_BASE}/v2/orders', params={'status': 'open', 'limit': 500},
                         headers=_alpaca_hdrs(), timeout=10)
        if r.status_code != 200:
            return None
        out = {}
        for o in (r.json() or []):
            if not isinstance(o, dict):
                continue
            sym = str(o.get('symbol') or '').replace('/', '').upper()
            out.setdefault(sym, set()).add(str(o.get('side') or '').strip().lower())
        return out
    except Exception:  # noqa: BLE001
        return None


def _agent_get_account() -> dict:
    if not ALPACA_KEY:
        _AGENT['broker_error'] = 'ALPACA_KEY sin configurar · ALPACA_KEY not configured'
        return {}
    try:
        r = requests.get(f'{ALPACA_BASE}/v2/account', headers=_alpaca_hdrs(), timeout=10)
        if r.status_code == 200:
            _AGENT['broker_error'] = None
            return r.json() or {}
        # Guardamos el status y un extracto del cuerpo para depurar (p.ej. 404 por
        # base mal configurada, 401/403 por claves inválidas).
        _AGENT['broker_error'] = f'Alpaca /v2/account HTTP {r.status_code}: {(r.text or "")[:120]}'
    except Exception as e:  # noqa: BLE001
        _AGENT['broker_error'] = f'Alpaca /v2/account: {_diag_redact(e)[:120]}'
    return {}


def _alpaca_tradable(sym):
    """¿Alpaca opera este símbolo? Caché 24 h. Si no se puede verificar → True
    (que Alpaca decida; su rechazo queda registrado como ERROR)."""
    e = _TRADABLE_CACHE.get(sym)
    if e and time.time() - e[0] < 86400:
        return e[1]
    try:
        from urllib.parse import quote as _q
        r = requests.get(f'{ALPACA_BASE}/v2/assets/{_q(sym, safe="")}', headers=_alpaca_hdrs(), timeout=8)
        if r.status_code == 404:
            ok = False
        elif r.status_code == 200:
            a = r.json() or {}
            ok = bool(a.get('tradable')) and str(a.get('status') or 'active') == 'active'
        else:
            return True
    except Exception:  # noqa: BLE001
        return True
    _TRADABLE_CACHE[sym] = (time.time(), ok)
    return ok


def _agent_submit(body, action, detail):
    """POST /v2/orders. 2xx con id → payload; si no → _AgentOrderError. Audita SIEMPRE."""
    body = dict(body)
    body.setdefault('client_order_id', 'kh-agent-' + uuid.uuid4().hex[:24])
    detail = dict(detail, client_order_id=body['client_order_id'], tif=body.get('time_in_force'))
    try:
        r = requests.post(f'{ALPACA_BASE}/v2/orders', headers=_alpaca_hdrs(), json=body, timeout=15)
    except Exception as e:  # noqa: BLE001
        _trade_audit(action, dict(detail, outcome='unknown_error', error=type(e).__name__), actor='agente-trading')
        raise _AgentOrderError(f'sin respuesta de Alpaca · no answer from Alpaca ({type(e).__name__})') from e
    payload = _alpaca_json(r)
    ok = 200 <= r.status_code < 300 and isinstance(payload, dict) and bool(payload.get('id'))
    msg = ''
    if isinstance(payload, dict):
        msg = str(payload.get('message') or payload.get('error') or '')[:140]
    elif r.text:
        msg = r.text[:140]
    _trade_audit(action, dict(detail, outcome='submitted' if ok else 'rejected', http_status=r.status_code,
                              alpaca_order_id=(payload.get('id') if isinstance(payload, dict) else None),
                              alpaca_status=(payload.get('status') if isinstance(payload, dict) else None),
                              alpaca_message=msg or None), actor='agente-trading')
    if not ok:
        raise _AgentOrderError(f'Alpaca HTTP {r.status_code}: {msg or "orden rechazada · order rejected"}')
    return payload


def _agent_place(ticker: str, side: str, notional: float) -> dict:
    """Orden market por monto (USD). Lanza _AgentOrderError si Alpaca no la acepta."""
    body = {
        'symbol': ticker,
        'notional': f'{notional:.2f}',
        'side': side,
        'type': 'market',
        'time_in_force': 'gtc' if '/' in ticker else 'day',   # cripto: Alpaca exige gtc/ioc
    }
    return _agent_submit(body, 'agent_order', {'symbol': ticker, 'side': side, 'notional': round(notional, 2)})


def _agent_stop_losses(positions, block):
    """Cierra las posiciones que superan el stop. Devuelve los símbolos tocados
    (no se vuelve a operar sobre ellos en este ciclo)."""
    touched = set()
    now = time.time()
    pend = _AGENT.setdefault('pending_close', {})
    for k in [k for k, ts in pend.items() if now - ts > _AGENT_PENDING_CLOSE_S]:
        pend.pop(k, None)
    open_syms = None
    for sym, p in list(positions.items()):
        try:
            pl_pct = float(p.get('unrealized_plpc') or 0) * 100
            qty = float(p.get('qty') or 0)
        except (TypeError, ValueError):
            continue
        if not qty or pl_pct > -_AGENT['stop_loss_pct']:
            continue
        key = str(sym).replace('/', '').upper()
        close_side = 'sell' if qty > 0 else 'buy'
        touched.add(sym)
        if block:
            _agent_log({'ticker': sym, 'level': 'warn',
                        'msg': f'🛑 Stop-loss {pl_pct:.1f}% NO enviado · NOT sent — {block}'})
            continue
        if open_syms is None:
            open_syms = _agent_open_order_symbols()
        # Solo cuenta como "cierre pendiente" una orden abierta del lado que CIERRA
        # (venta si es larga, compra si es corta); una del otro lado no apaga el stop.
        if key in pend or (open_syms is not None and close_side in open_syms.get(key, ())):
            _agent_log({'ticker': sym, 'level': 'info',
                        'msg': '⏳ Stop-loss: ya hay un cierre pendiente — no se reenvía · close already pending'})
            continue
        is_crypto = str(p.get('asset_class') or '') == 'crypto' or '/' in str(sym)
        body = {'symbol': sym, 'qty': _num_str(abs(qty)), 'side': close_side,
                'type': 'market', 'time_in_force': 'gtc' if is_crypto else 'day'}
        try:
            res = _agent_submit(body, 'agent_stop_loss', {'symbol': sym, 'side': body['side'], 'qty': body['qty'],
                                                           'pl_pct': round(pl_pct, 2)})
            pend[key] = now
            _agent_log({'ticker': sym, 'level': 'warn', 'order_id': str(res.get('id') or '')[:12],
                        'msg': f'🛑 Stop-loss {pl_pct:.1f}% — orden de cierre enviada · close order sent '
                               f'({res.get("status") or "accepted"})'})
        except Exception as e:  # noqa: BLE001
            _agent_log({'ticker': sym, 'level': 'error',
                        'msg': f'Stop-loss error: {_diag_redact(e)[:160]}'})
    return touched


def _agent_run_cycle():
    """One analysis + execution cycle for all tickers in universe."""
    account = _agent_get_account()
    equity = float(account.get('equity', 0) or 0)
    if equity <= 0 and ALPACA_KEY:
        be = _AGENT.get('broker_error') or 'Alpaca no devolvió capital · Alpaca returned no equity'
        _agent_log({'level': 'warn',
                    'msg': f'⚠️ No se pudo leer el capital de Alpaca · Could not read Alpaca equity — {be}'})
        return

    # P&L real del día desde Alpaca (equity vs cierre de ayer) — sin esto el
    # circuit-breaker de abajo nunca puede saltar
    last_equity = float(account.get('last_equity', 0) or 0)
    if last_equity > 0:
        _AGENT['daily_pnl_pct'] = (equity - last_equity) / last_equity * 100

    # Circuit-breaker diario: bloquea ENTRADAS NUEVAS pero NUNCA la protección
    # de salida (auditoría Track D 2026-08-01).
    breaker_on = _AGENT['daily_pnl_pct'] <= -_AGENT['max_daily_loss_pct']
    if breaker_on:
        _agent_log({'level': 'warn',
                    'msg': f'🛑 Daily loss limit hit ({_AGENT["daily_pnl_pct"]:.2f}%) — sin entradas nuevas; stop-loss sigue activo'})

    auto = _AGENT['mode'] == 'auto'
    block = _agent_exec_block(account) if auto else None
    if block:
        _agent_log({'level': 'warn', 'msg': f'⏸ Órdenes en pausa · Orders paused — {block}'})

    positions = _agent_get_positions()
    stopped = _agent_stop_losses(positions, block) if auto else set()
    for sym in stopped:
        positions.pop(sym, None)

    # Con el breaker activo (o las órdenes en pausa) y en modo auto no hay nada
    # que ejecutar: ahorramos además el costo de analizar 10-30 tickers con IA.
    # En modo manual (solo consejos) se sigue analizando — el log asesor no
    # abre posiciones.
    if auto and (breaker_on or block):
        _AGENT['last_run'] = time.strftime('%Y-%m-%d %H:%M:%S')
        return

    universe, _skipped = _agent_universe(_AGENT['universe'])
    orders_this_cycle = 0
    for ticker in universe or []:
        if not _AGENT['running']:
            break
        price, prev, sentiment = 0.0, 0.0, 0.0
        if FINNHUB:
            data, err = _fetch_quote_raw(ticker, timeout=8)
            if not err and isinstance(data, dict):
                try:
                    price = float(data.get('c') or 0)
                    prev = float(data.get('pc') or 0)
                except (TypeError, ValueError):
                    price = 0.0

        # lightweight GDELT sentiment
        try:
            gr = requests.get('https://api.gdeltproject.org/api/v2/doc/doc',
                              params={'query': ticker, 'mode': 'tonechart', 'format': 'json', 'maxrecords': 5},
                              timeout=6)
            gdata = gr.json()
            tones = [float(x.get('avgtone', 0) or 0) for x in (gdata.get('tonechart') or [])[:5]]
            sentiment = sum(tones) / len(tones) if tones else 0.0
        except Exception:  # noqa: BLE001
            pass

        if price <= 0:
            continue

        action, confidence, reason, size_pct = _agent_clean_analysis(_agent_analyze(ticker, price, prev, sentiment))
        entry = {
            'ts': time.strftime('%H:%M:%S'),
            'ticker': ticker,
            'price': price,
            'action': action,
            'confidence': confidence,
            'reason': reason,
            'executed': False,
            'level': 'info',
        }

        if auto and ALPACA_KEY and action != 'hold' and confidence >= _AGENT.get('min_confidence', 65):
            # Endurecimientos (auditoría Track D): freno duro de órdenes por
            # ciclo, no acumular por encima del tope en el mismo ticker, y no
            # vender sin tenencia (evita shorts no intencionados con margen).
            existing = positions.get(ticker) or {}
            try:
                existing_mv = abs(float(existing.get('market_value') or 0))
            except (TypeError, ValueError):
                existing_mv = 0.0
            skip = None
            if block:
                skip = block
            elif ticker in stopped:
                skip = 'stop-loss en este ciclo · stop-loss this cycle'
            elif orders_this_cycle >= _AGENT.get('max_orders_per_cycle', 3):
                skip = 'freno: tope de órdenes por ciclo'
            elif size_pct <= 0:
                skip = 'tamaño 0 · size 0'
            elif action == 'buy' and equity > 0 and existing_mv >= equity * _AGENT['max_pos_pct'] / 100:
                skip = f'posición ya en tope ({existing_mv / equity * 100:.1f}% ≥ {_AGENT["max_pos_pct"]}%)'
            elif action == 'sell' and not existing:
                skip = 'sin tenencia — no se abre corto'
            elif not _alpaca_tradable(ticker):
                skip = 'no operable en Alpaca · not tradable on Alpaca'
            if skip:
                entry['skipped'] = skip
            else:
                notional = equity * size_pct / 100
                notional = max(1.0, min(notional, equity * _AGENT['max_pos_pct'] / 100, MAX_ORDER_USD))
                if action == 'buy' and equity > 0:
                    # que la orden no empuje la posición total por encima del tope
                    room = equity * _AGENT['max_pos_pct'] / 100 - existing_mv
                    notional = min(notional, max(1.0, room))
                try:
                    result = _agent_place(ticker, action, notional)
                    entry['executed'] = True
                    entry['order_id'] = str(result.get('id') or '')[:12]
                    entry['order_status'] = result.get('status')
                    entry['notional'] = round(notional, 2)
                    entry['level'] = 'success'
                    orders_this_cycle += 1
                except Exception as e:  # noqa: BLE001 — rechazo de Alpaca o red: ERROR, no ejecutada
                    entry['exec_error'] = _diag_redact(e)[:160]
                    entry['level'] = 'error'

        _agent_log(entry)

    _AGENT['last_run'] = time.strftime('%Y-%m-%d %H:%M:%S')


def _agent_thread_fn():
    _AGENT['status'] = 'running'
    try:
        while _AGENT['running']:
            try:
                _agent_run_cycle()
            except Exception as e:  # noqa: BLE001
                _agent_log({'msg': f'Cycle error: {_diag_redact(e)}', 'level': 'error'})
            lo, hi, _t = _AGENT_BOUNDS['interval_min']
            interval = int(min(hi, max(lo, _AGENT['interval_min']))) * 60
            for _ in range(interval):
                if not _AGENT['running']:
                    break
                time.sleep(1)
    finally:
        _AGENT['status'] = 'stopped'


@app.route('/api/trade/agent/start', methods=['POST'])
@rate_limit(limit=10, window=60)
@_trade_auth
def agent_start():
    if not ALPACA_KEY:
        return _broker_missing_response()
    data, bad = _json_object_body()
    if bad:
        return bad
    changes, notes, err = _agent_parse(data)
    if err:
        return _bad(*err)
    if changes.get('mode', _AGENT['mode']) == 'auto' and not _paper():
        return _auto_live_refused()
    with _AGENT_LOCK:
        _AGENT.update(changes)
        if _AGENT['running']:
            return jsonify({'status': 'already_running', 'mode': _AGENT['mode'], 'notes': notes,
                            'config': _agent_config_view()})
        prev_t = _AGENT.get('thread')
        if prev_t is not None and prev_t.is_alive():
            return _bad('El agente aún se está deteniendo; reintenta en unos segundos',
                        'The agent is still stopping; retry in a few seconds', code='agent_stopping', status=409)
        _AGENT['running'] = True
        _AGENT['daily_pnl_pct'] = 0.0
        t = threading.Thread(target=_agent_thread_fn, daemon=True, name='khipu-trading-agent')
        _AGENT['thread'] = t
        t.start()
    _trade_audit('agent_start', {'outcome': 'started', **{k: v for k, v in _agent_config_view().items()
                                                          if k != 'universe'},
                                 'universe_n': len(_AGENT['universe'])})
    return jsonify({'status': 'started', 'mode': _AGENT['mode'], 'paper': _paper(), 'notes': notes,
                    'config': _agent_config_view()})


@app.route('/api/trade/agent/stop', methods=['POST'])
@rate_limit(limit=20, window=60)
@_trade_auth
def agent_stop():
    with _AGENT_LOCK:
        _AGENT['running'] = False
    _trade_audit('agent_stop', {'outcome': 'stopping'})
    return jsonify({'status': 'stopping'})


@app.route('/api/trade/agent/status', methods=['GET'])
@rate_limit(limit=120, window=60)
@_trade_auth
def agent_status():
    with _AGENT_LOG_LOCK:
        recent = list(_AGENT['log'][-20:])
    return jsonify({
        'running': _AGENT['running'],
        'status': _AGENT['status'],
        'mode': _AGENT['mode'],
        'interval_min': _AGENT['interval_min'],
        'universe': _AGENT['universe'],
        'max_pos_pct': _AGENT['max_pos_pct'],
        'max_daily_loss_pct': _AGENT['max_daily_loss_pct'],
        'stop_loss_pct': _AGENT['stop_loss_pct'],
        'min_confidence': _AGENT.get('min_confidence', 65),
        'max_orders_per_cycle': _AGENT.get('max_orders_per_cycle', 3),
        'paper': _paper(),
        'auto_allowed': _paper(),
        'trading_enabled': _house_trading_enabled(),
        'bounds': {k: [lo, hi] for k, (lo, hi, _t) in _AGENT_BOUNDS.items()},
        'last_run': _AGENT['last_run'],
        'daily_pnl_pct': _AGENT['daily_pnl_pct'],
        'broker_error': _AGENT.get('broker_error'),
        'log': recent,
    })


@app.route('/api/trade/agent/config', methods=['POST'])
@rate_limit(limit=20, window=60)
@_trade_auth
def agent_config():
    data, bad = _json_object_body()
    if bad:
        return bad
    changes, notes, err = _agent_parse(data)
    if err:
        return _bad(*err)
    if changes.get('mode', _AGENT['mode']) == 'auto' and not _paper():
        return _auto_live_refused()
    with _AGENT_LOCK:
        _AGENT.update(changes)
    if changes:
        _trade_audit('agent_config', {'outcome': 'updated', **{k: v for k, v in changes.items() if k != 'universe'},
                                      **({'universe_n': len(changes['universe'])} if 'universe' in changes else {})})
    return jsonify({'status': 'updated', 'notes': notes, **_agent_config_view()})


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
        text, model = _ai_complete(system, prompt, max_tokens=900, model='claude-sonnet-5')
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
