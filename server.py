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
# pero el resto del servidor (proxy de datos, voz Bixby) sigue funcionando.
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(message)s')
log = logging.getLogger('khipu')

# ── Ontología (Fase 1, opcional) — /api/ontology/* ───────────────────────────
# Registro defensivo: si sqlalchemy no está instalado aún (deploy en curso) o
# DATABASE_URL no está configurada, el resto de la app sigue funcionando igual.
try:
    from ontology.api import ontology_bp
    app.register_blueprint(ontology_bp)
except Exception as _e:  # noqa: BLE001
    log.warning('Ontología no registrada (opcional): %s', _e)

# ── Motor de matrices (Etapa 3, opcional) — /api/matrix/* ────────────────────
try:
    from matrix.api import matrix_bp
    app.register_blueprint(matrix_bp)
except Exception as _e:  # noqa: BLE001
    log.warning('Motor de matrices no registrado (opcional): %s', _e)

# ── Re-migración de la ontología por variable de entorno (para Fabrizio) ──────
# Poner REMIGRATE_ON_BOOT=1 en Railway → al reiniciar, re-crea la ontología con
# los datos canónicos limpios (407). DESTRUCTIVO (borra objetos/eventos de la
# ontología, incl. tesis/sims/alertas guardadas). Se corre UNA vez y luego se
# quita la variable. Nunca bloquea el arranque (todo en try/except).
if os.getenv('REMIGRATE_ON_BOOT', '').strip() in ('1', 'true', 'yes'):
    try:
        from scripts.migrate_v0_to_ontology import run_migration
        log.warning('REMIGRATE_ON_BOOT activo — re-migrando la ontología a los 407 canónicos…')
        run_migration(reset=True, log=lambda m: log.warning('  [remigrate] %s', m))
        log.warning('REMIGRATE_ON_BOOT: listo. QUITA la variable REMIGRATE_ON_BOOT de Railway ahora.')
    except Exception as _e:  # noqa: BLE001
        log.error('REMIGRATE_ON_BOOT falló (la app sigue): %s', _e)

# Config compartida server/ontology (keys de IA, Finnhub, timeout) → core/config.py
# Helpers compartidos: cascada de IA, quote crudo y GET saneado → core/*.py
from core.config import (AI_MODEL, AI_ORDER, CLAUDE, FINNHUB, GEMINI_KEY,
                         GEMINI_MODEL, HTTP_TIMEOUT, NVIDIA_KEY, NVIDIA_MODEL)
from core.http import _safe_get, _safe_ticker
from core.ai import _ai_complete, _ai_configured, _claude_complete, _extract_json
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
MIROFISH_URL        = os.getenv('MIROFISH_URL', 'https://mirofish-fika.up.railway.app')
MIROFISH_TOKEN      = os.getenv('MIROFISH_TOKEN', '')
ELEVENLABS_KEY      = os.getenv('ELEVENLABS_KEY', '')
ELEVENLABS_AGENT_ID = os.getenv('ELEVENLABS_AGENT_ID', '')
AV_KEY              = os.getenv('AV_KEY') or os.getenv('ALPHA_VANTAGE_KEY', '')
SECRET_KEY          = os.getenv('SECRET_KEY', 'khipu-dev-secret-change-me')
ALPACA_KEY          = os.getenv('ALPACA_KEY', '')
ALPACA_SECRET       = os.getenv('ALPACA_SECRET', '')
ALPACA_BASE         = os.getenv('ALPACA_BASE', 'https://paper-api.alpaca.markets')
# PIN que protege TODAS las rutas /api/trade/* (operan dinero real vía Alpaca).
# Sin TRADE_PIN configurado, el trading queda DESHABILITADO (seguro por defecto).
TRADE_PIN           = os.getenv('TRADE_PIN', '')
# Secreto de administrador para emitir claves /v1 de tiers de pago.
KHIPU_ADMIN_SECRET  = os.getenv('KHIPU_ADMIN_SECRET', '')

if SECRET_KEY == 'khipu-dev-secret-change-me':
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

# ── Simple in-process rate limiter ──────────────────────────────────────────
_rate_buckets: dict = defaultdict(list)

def _rate_limit(key: str, limit: int, window: int) -> bool:
    """Returns True if request is allowed. key=ip+endpoint, limit=max calls, window=seconds."""
    now = time.time()
    bucket = _rate_buckets[key]
    _rate_buckets[key] = [t for t in bucket if now - t < window]
    if len(_rate_buckets[key]) >= limit:
        return False
    _rate_buckets[key].append(now)
    return True

def rate_limit(limit: int, window: int = 3600):
    """Decorator: limit calls per IP. limit=max, window=seconds (default 1 hour)."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown').split(',')[0].strip()
            key = f'{ip}:{f.__name__}'
            if not _rate_limit(key, limit, window):
                log.warning('Rate limit hit: %s %s', ip, f.__name__)
                return jsonify({'error': 'Rate limit exceeded. Try again later.'}), 429
            return f(*args, **kwargs)
        return wrapper
    return decorator


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
    '"name":"Khipu Finance","short_name":"KhipuFi","display":"standalone",'
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

@app.route('/nodes/<path:filename>')
def serve_nodes(filename):
    from flask import send_from_directory
    resp = send_from_directory(os.path.join(_APP_DIR, 'nodes'), filename, mimetype='application/javascript')
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp

@app.route('/engine/<path:filename>')
def serve_engine(filename):
    from flask import send_from_directory
    resp = send_from_directory(os.path.join(_APP_DIR, 'engine'), filename, mimetype='application/javascript')
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp

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
}


@app.route('/vendor/<path:name>')
@cache.cached(timeout=604800)  # 7 días
def vendor(name):
    url = _VENDOR_MAP.get(name)
    if not url:
        return jsonify({'error': 'unknown vendor asset'}), 404
    try:
        r = requests.get(url, timeout=25, headers={'User-Agent': 'KhipuFinance/1.0'})
        if not r.ok:
            return jsonify({'error': f'upstream {r.status_code}'}), 502
        ctype = (r.headers.get('Content-Type') or '').split(';')[0] or \
            ('application/javascript' if name.endswith('.js') else 'application/octet-stream')
        resp = app.response_class(r.content, mimetype=ctype)
        resp.headers['Cache-Control'] = 'public, max-age=604800'
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:120]}), 502


# ----------------------------------------------------------------------------
# Health check / data-health (extendido: incluye MiroFish, ElevenLabs)
# ----------------------------------------------------------------------------
@app.route('/api/health')
def health():
    mf_ok = False
    try:
        mf_ok = requests.get(f'{MIROFISH_URL}/api/health', timeout=2).ok
    except Exception:  # noqa: BLE001
        pass
    return jsonify({
        'server': True,
        'app': 'Khipus AI Finance Inteligence',
        'assistant': 'Bixby',
        'finnhub': bool(FINNHUB),
        'fmp': bool(FMP),
        'claude': bool(CLAUDE),
        'gemini': bool(GEMINI_KEY),
        'nvidia': bool(NVIDIA_KEY),
        'marketstack': bool(MSTACK),
        'elevenlabs': bool(ELEVENLABS_KEY),
        'alpha_vantage': bool(AV_KEY),
        'mirofish': mf_ok,
        'jwt_api': _HAS_JWT,
        'ai_model': AI_MODEL,
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
    """Quita cualquier valor de key que pudiera aparecer en un mensaje de error."""
    s = str(text)[:200]
    for secret in (CLAUDE, ELEVENLABS_KEY, FINNHUB, FMP, MSTACK, AV_KEY, MIROFISH_TOKEN, SECRET_KEY,
                   NEO4J_PASSWORD, NEO4J_URI):
        if secret and len(secret) > 6 and secret in s:
            s = s.replace(secret, '••••')
    return s


def _diag_claude():
    if not CLAUDE:
        return {'configured': False, 'ok': False,
                'detail': 'ANTHROPIC_KEY no está en las variables del servidor (Railway). '
                          'Sin ella: Canvas IA, análisis de Bixby y el fallback del War-Room fallan.'}
    t0 = time.time()
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=CLAUDE)
        msg = client.messages.create(
            model=AI_MODEL, max_tokens=1,
            messages=[{'role': 'user', 'content': 'ping'}],
        )
        return {'configured': True, 'ok': True, 'latency_ms': int((time.time() - t0) * 1000),
                'detail': f'Key válida — modelo {msg.model} respondió.'}
    except Exception as e:  # noqa: BLE001
        return {'configured': True, 'ok': False, 'latency_ms': int((time.time() - t0) * 1000),
                'detail': 'Key presente pero la API rechazó la llamada: ' + _diag_redact(e)}


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
        return {'configured': True, 'ok': False, 'latency_ms': int((time.time() - t0) * 1000),
                'detail': 'Gemini rechazó la llamada: ' + _diag_redact(e)}


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
        return {'configured': True, 'ok': False, 'latency_ms': int((time.time() - t0) * 1000),
                'detail': 'NVIDIA rechazó la llamada: ' + _diag_redact(e)}


def _diag_elevenlabs():
    if not ELEVENLABS_KEY:
        return {'configured': False, 'ok': False, 'agent_configured': bool(ELEVENLABS_AGENT_ID),
                'detail': 'ELEVENLABS_KEY no está en el servidor. Bixby (voz) no podrá conectar.'}
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
            detail = 'Key válida, pero falta ELEVENLABS_AGENT_ID — Bixby no sabe a qué agente conectar.'
            ok = False
        elif agent_ok:
            detail = 'Key válida y agente encontrado. Bixby debería conectar.'
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


def _diag_mirofish():
    """Prueba ambas rutas (/api/health y /health) porque hubo inconsistencia histórica."""
    t0 = time.time()
    last = ''
    for path in ('/api/health', '/health'):
        try:
            r = requests.get(f'{MIROFISH_URL}{path}', headers=_mf_headers(), timeout=6)
            if r.ok:
                return {'configured': True, 'ok': True, 'token_set': bool(MIROFISH_TOKEN),
                        'latency_ms': int((time.time() - t0) * 1000), 'working_path': path,
                        'detail': f'MiroFish vivo en {path}. War-Room puede usar el motor real.'}
            last = f'{path} → HTTP {r.status_code}'
        except Exception as e:  # noqa: BLE001
            last = f'{path} → ' + _diag_redact(e)
    hint = '' if MIROFISH_TOKEN else ' (no hay MIROFISH_TOKEN configurado — puede requerir auth).'
    return {'configured': True, 'ok': False, 'token_set': bool(MIROFISH_TOKEN),
            'latency_ms': int((time.time() - t0) * 1000),
            'detail': f'MiroFish no responde OK: {last}.{hint} El War-Room usará el fallback de Claude.'}


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
        return {'configured': True, 'ok': False, 'detail': 'Ontología configurada pero no conecta: ' + _diag_redact(e)}


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
                'detail': 'NEO4J configurado pero no conecta: ' + _diag_redact(e) + ctx + warn}


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
        'mirofish':   _diag_mirofish(),
        'finnhub':    _diag_finnhub(),
        'grafo':      _diag_grafo(),
        'ontologia':  _diag_ontologia(),
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
    }
    _DIAG_CACHE['ts'] = now
    _DIAG_CACHE['data'] = out
    return jsonify(out)


# ----------------------------------------------------------------------------
# Finnhub — precios, noticias, earnings, WebSocket token
# ----------------------------------------------------------------------------
@app.route('/api/ws-token')
@rate_limit(limit=30, window=60)  # 30 tokens per minute per IP
def ws_token():
    """Returns a short-lived signed token the browser uses to open the Finnhub WebSocket.
    The token expires in 30 seconds and is HMAC-signed so it cannot be forged.
    The browser must exchange it for the real key at connect time via /api/ws-key."""
    if not FINNHUB:
        return jsonify({'error': 'no FINNHUB_KEY'}), 400
    expires = int(time.time()) + 30
    payload = f'ws:{expires}'
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    return jsonify({'session_token': f'{expires}.{sig}', 'expires_in': 30})


@app.route('/api/ws-key', methods=['POST'])
@rate_limit(limit=30, window=60)
def ws_key():
    """Validates a session_token and returns the real Finnhub key. Token must be fresh (<30s)."""
    if not FINNHUB:
        return jsonify({'error': 'no FINNHUB_KEY'}), 400
    data = request.get_json(silent=True) or {}
    token = data.get('session_token', '')
    try:
        parts = token.split('.')
        expires = int(parts[0])
        sig = parts[1]
    except (ValueError, IndexError):
        return jsonify({'error': 'invalid token'}), 401
    if time.time() > expires:
        return jsonify({'error': 'token expired'}), 401
    payload = f'ws:{expires}'
    expected = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(sig, expected):
        return jsonify({'error': 'invalid token signature'}), 401
    return jsonify({'token': FINNHUB})


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


@app.route('/api/quotes')
@rate_limit(limit=120, window=60)
@cache.cached(timeout=15, query_string=True)
def batch_quotes():
    if not FINNHUB:
        return jsonify({'error': 'no FINNHUB_KEY'}), 400
    tickers = [s for s in (_safe_ticker(t) for t in request.args.get('symbols', '').split(',')) if s]
    results = {}
    for t in tickers[:60]:  # límite de cortesía por request
        data, err = _fetch_quote_raw(t, timeout=4)
        if data:
            results[t] = data
    return jsonify(results)


# ── Series anuales para el DOSSIER financiero (estilo investingvisuals) ─────
# OJO: /api/fundamentals/<t> ya existe (P/E + price targets + ratings, lo usa
# el Second Brain) — este es OTRO endpoint con las series anuales de 6 años.
@app.route('/api/findossier/<ticker>')
@rate_limit(limit=60, window=3600)
def fin_dossier(ticker):
    """Series anuales para el dossier financiero de una empresa:
    crecimiento de ingresos, dilución, FCF, márgenes, deuda/capital, ROE y
    EV/Ventas. Fuente: FMP (estados anuales, ~5 años). Sin FMP_KEY responde
    {available:false} y el cliente lo muestra con gracia.
    Caché MANUAL solo de éxitos — un rate-limit de FMP no debe quedar
    envenenado 24h (mismo patrón que /api/fundamentals)."""
    ticker = _safe_ticker(ticker)
    if not ticker:
        return jsonify({'error': 'invalid ticker'}), 400
    if not FMP:
        return jsonify({'available': False, 'reason': 'FMP_KEY no configurada'})
    _ck = f'findossier_{ticker}'
    _hit = cache.get(_ck)
    if _hit is not None:
        return jsonify(_hit)

    # FMP "stable" primero (los planes nuevos NO soportan /api/v3 — el resto
    # del server ya usa /stable/); v3 como respaldo para planes antiguos.
    _last_err = {}

    def _fmp(resource):
        data, err = _safe_get(
            f'https://financialmodelingprep.com/stable/{resource}?symbol={ticker}&limit=6&apikey={FMP}')
        if isinstance(data, list) and data:
            return data
        if isinstance(data, dict):
            _last_err[resource] = str(data.get('Error Message') or data.get('message') or data)[:150]
        elif err:
            _last_err[resource] = str(err)[:150]
        data, err = _safe_get(
            f'https://financialmodelingprep.com/api/v3/{resource}/{ticker}?limit=6&apikey={FMP}')
        if isinstance(data, list) and data:
            return data
        if isinstance(data, dict):
            _last_err[resource] = str(data.get('Error Message') or data.get('message') or data)[:150]
        return []

    inc = _fmp('income-statement')
    cfs = _fmp('cash-flow-statement')
    bal = _fmp('balance-sheet-statement')
    km = _fmp('key-metrics')
    if not inc and AV_KEY:
        # Respaldo: Alpha Vantage (el plan gratis SÍ incluye estados anuales).
        # El plan FMP de producción devuelve 402 en statements (2026-07-11).
        def _av(fn):
            data, _e = _safe_get(f'https://www.alphavantage.co/query?function={fn}&symbol={ticker}&apikey={AV_KEY}')
            if isinstance(data, dict):
                note = data.get('Note') or data.get('Information') or data.get('Error Message')
                if note:
                    _last_err['av_' + fn] = str(note)[:160]
                return data.get('annualReports') or []
            return []

        # AV free = 1 request/segundo — espaciar las 3 llamadas (total ~2.4s,
        # tolerable: el dossier completo queda cacheado 24h por ticker)
        inc_av = _av('INCOME_STATEMENT')
        time.sleep(1.2)
        bal_av = _av('BALANCE_SHEET')
        time.sleep(1.2)
        cfs_av = _av('CASH_FLOW')
        if inc_av:
            def _y(r):
                return str(r.get('fiscalDateEnding', ''))[:4]
            sh_by_year = {_y(r): r.get('commonStockSharesOutstanding') for r in bal_av}
            inc = [{'calendarYear': _y(r), 'revenue': r.get('totalRevenue'),
                    'grossProfit': r.get('grossProfit'), 'netIncome': r.get('netIncome'),
                    'weightedAverageShsOut': sh_by_year.get(_y(r))} for r in inc_av[:6]]
            bal = [{'calendarYear': _y(r), 'totalDebt': r.get('shortLongTermDebtTotal'),
                    'totalStockholdersEquity': r.get('totalShareholderEquity')} for r in bal_av[:6]]
            cfs = []
            for r in cfs_av[:6]:
                try:
                    fcf_v = float(r.get('operatingCashflow') or 0) - float(r.get('capitalExpenditures') or 0)
                except (TypeError, ValueError):
                    fcf_v = None
                cfs.append({'calendarYear': _y(r), 'freeCashFlow': fcf_v})
            km = []   # AV no trae EV/Ventas — ese mini-gráfico queda vacío
    if not inc:
        return jsonify({'available': False,
                        'reason': _last_err.get('income-statement', 'sin estados financieros para este ticker/plan')})

    def by_year(rows):
        out = {}
        for r in (rows if isinstance(rows, list) else []):
            y = str(r.get('calendarYear') or r.get('date', ''))[:4]
            if y.isdigit():
                out[y] = r
        return out

    yi, yc, yb, yk = by_year(inc), by_year(cfs), by_year(bal), by_year(km)
    years = sorted(yi.keys())[-6:]

    def _f(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    series = {'years': [], 'revenue': [], 'revenue_growth': [], 'gross_margin': [],
              'fcf': [], 'fcf_margin': [], 'fcf_growth': [], 'dilution': [],
              'de_ratio': [], 'roe': [], 'ev_to_sales': []}
    prev_rev = prev_fcf = prev_sh = None
    for y in years:
        i, c, b, k = yi.get(y, {}), yc.get(y, {}), yb.get(y, {}), yk.get(y, {})
        rev = _f(i.get('revenue'))
        fcf = _f(c.get('freeCashFlow'))
        sh = _f(i.get('weightedAverageShsOut')) or _f(i.get('weightedAverageShsOutDil'))
        debt = _f(b.get('totalDebt'))
        eq = _f(b.get('totalStockholdersEquity')) or _f(b.get('totalEquity'))
        # márgenes/ratios: usar el campo directo si está, si no calcular del crudo
        gm = _f(i.get('grossProfitRatio'))
        if gm is None and rev and _f(i.get('grossProfit')) is not None:
            gm = _f(i.get('grossProfit')) / rev
        roe = _f(k.get('roe')) or _f(k.get('returnOnEquity'))
        if roe is None and eq and _f(i.get('netIncome')) is not None:
            roe = _f(i.get('netIncome')) / eq
        evs = _f(k.get('evToSales')) or _f(k.get('enterpriseValueOverRevenue')) \
            or _f(k.get('evToRevenue'))
        series['years'].append(y)
        series['revenue'].append(rev)
        series['revenue_growth'].append(round((rev / prev_rev - 1) * 100, 1) if rev and prev_rev else None)
        series['gross_margin'].append(round(gm * 100, 1) if gm is not None else None)
        series['fcf'].append(fcf)
        series['fcf_margin'].append(round(fcf / rev * 100, 1) if fcf is not None and rev else None)
        series['fcf_growth'].append(round((fcf / prev_fcf - 1) * 100, 1) if fcf and prev_fcf and prev_fcf > 0 else None)
        series['dilution'].append(round((sh / prev_sh - 1) * 100, 2) if sh and prev_sh else None)
        series['de_ratio'].append(round(debt / eq, 3) if debt is not None and eq else None)
        series['roe'].append(round(roe * 100, 1) if roe is not None else None)
        series['ev_to_sales'].append(round(evs, 1) if evs is not None else None)
        prev_rev, prev_fcf, prev_sh = rev, fcf, sh

    payload = {'available': True, 'ticker': ticker, **series}
    if _last_err:
        payload['partial'] = {k: v for k, v in _last_err.items()}   # diagnóstico visible
    # caché: 24h si llegó el paquete completo; si balance/FCF vinieron vacíos
    # (rate-limit transitorio) NO cachear — que el próximo intento lo complete
    complete = any(v is not None for v in series['dilution']) and any(v is not None for v in series['fcf'])
    if complete:
        cache.set(_ck, payload, timeout=86400)
    return jsonify(payload)


@app.route('/api/candles/<ticker>')
@rate_limit(limit=120, window=60)
@cache.cached(timeout=1800)
def candles(ticker):
    """90 days of daily OHLCV candles for charting.

    Tries Finnhub → FMP → Stooq (Stooq is free / no key) so the chart works
    regardless of which paid API tier is configured. Always returns the
    Finnhub-style shape {s,c,o,h,l,t} the frontend expects.
    """
    ticker = _safe_ticker(ticker)
    if not ticker:
        return jsonify({'error': 'invalid ticker', 's': 'no_data'}), 400
    import time as _time
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


def _trade_auth(f):
    """Exige el PIN de trading (header X-Trade-Pin == env TRADE_PIN).

    Estas rutas mueven dinero real en Alpaca y exponen datos de la cuenta:
    sin este guard, cualquiera con la URL pública puede operar. Sin TRADE_PIN
    en el entorno el trading queda deshabilitado por completo."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not TRADE_PIN:
            return jsonify({'error': 'Trading deshabilitado — configura TRADE_PIN en Railway',
                            'code': 'trading_disabled'}), 403
        pin = request.headers.get('X-Trade-Pin', '')
        if not hmac.compare_digest(pin, TRADE_PIN):
            return jsonify({'error': 'PIN de trading incorrecto o faltante',
                            'code': 'invalid_pin'}), 401
        return f(*args, **kwargs)
    return wrapper


@app.route('/api/trade/account', methods=['GET'])
@_trade_auth
def trade_account():
    if not ALPACA_KEY:
        return jsonify({'error': 'ALPACA_KEY not configured'}), 400
    try:
        r = requests.get(f'{ALPACA_BASE}/v2/account',
                         headers=_alpaca_hdrs(), timeout=10)
        try:
            return jsonify(r.json()), r.status_code
        except Exception:
            return jsonify({'error': f'Alpaca HTTP {r.status_code}', 'body': r.text[:300]}), 502
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200], 'base': ALPACA_BASE, 'key_set': bool(ALPACA_KEY)}), 502

@app.route('/api/trade/order', methods=['POST'])
@rate_limit(20, 60)
@_trade_auth
def trade_order():
    if not ALPACA_KEY:
        return jsonify({'error': 'ALPACA_KEY not configured'}), 400
    data   = request.get_json(silent=True) or {}
    ticker = (data.get('symbol') or '').upper().strip()
    qty    = data.get('qty')
    side   = data.get('side', 'buy')
    otype  = data.get('type', 'market')
    tif    = data.get('time_in_force', 'day')
    if not ticker or not qty or side not in ('buy', 'sell'):
        return jsonify({'error': 'symbol, qty y side (buy|sell) son requeridos'}), 400
    body = {'symbol': ticker, 'qty': str(qty), 'side': side,
            'type': otype, 'time_in_force': tif}
    try:
        r = requests.post(f'{ALPACA_BASE}/v2/orders',
                          headers=_alpaca_hdrs(), json=body, timeout=15)
        return jsonify(r.json()), r.status_code
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200]}), 502


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
        return jsonify([])
    return jsonify(data[:20])


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
        return jsonify({'earningsCalendar': []})
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
    cache_key = f'fund_{ticker}'
    hit = cache.get(cache_key)
    if hit is not None:
        return jsonify(hit)

    metrics = []
    targets = []
    ratings = []
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
    result = {'metrics': metrics, 'priceTarget': targets or [], 'ratings': ratings}
    # Solo cachear si obtuvimos algo — errores transitorios no deben quedarse 24h
    if metrics or targets or ratings:
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
        return jsonify([])
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
    # Clamp max_tokens to avoid runaway costs
    max_tok = min(int(data.get('max_tokens', 1000)), 2000)
    # caché 30 min por (system+prompt): el mismo análisis no paga otra llamada IA
    _ck = 'aian:' + hashlib.sha256(
        (str(data.get('system', '')) + '\x00' + str(data.get('prompt', ''))).encode('utf-8')
    ).hexdigest()[:24]
    _hit = cache.get(_ck)
    if _hit:
        return jsonify({'result': _hit['result'], 'model': _hit['model'], 'cached': True})
    try:
        text, model = _claude_complete(
            data.get('system', ''),
            data.get('prompt', ''),
            max_tok,
        )
        cache.set(_ck, {'result': text, 'model': model}, timeout=1800)
        return jsonify({'result': text, 'model': model})
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200]}), 500


# ── Bixby Canvas — AI-generated chart specs (Fase 1) ────────────────────────
_CANVAS_SYSTEM = """\
You are Khipu Finance's Canvas AI — an expert at semiconductor / AI / space supply chain analytics.
Given a user query and a JSON context with node data and market quotes, produce a single-screen
data visualization spec. Respond ONLY with valid JSON — no markdown fences, no explanation.

Supported types and their data schemas:
• bar     – data:[{label,value,color?}]              config:{unit?,axis_label?}
• line    – data:[{label,values:[n,…],color?}]       config:{unit?,series_labels:[…]}
• bubble  – data:[{id,label,x,y,r,color?}]           config:{x_label,y_label,r_label}
• treemap – data:[{label,value,color?,cat?}]          config:{}
• heatmap – data:[{row,col,value}]                   config:{rows:[…],cols:[…],unit?}
• radar   – data:[{label,values:[0-100,…]}]           config:{axes:[…]}  (≤3 series, 4-8 axes)
• scatter – data:[{label,x,y,color?}]                config:{x_label,y_label}
• table   – data:[{col:val,…}]                       config:{columns:[…]}

Always respond with exactly:
{"type":"<type>","title":"<concise title>","subtitle":"<1 sentence insight>","data":[…],"config":{…}}

Rules:
- bar: sort by value descending, max 20 items.
- table: max 15 rows; only the most relevant columns.
- radar: axes normalized 0-100; each data item is one company/series.
- heatmap: ≤10 rows, ≤10 cols.
- Use node data from context — do NOT invent prices or market caps not provided.
- nrs field in nodes is already a 0-100 score (Node Risk/Resilience Score).
- context.live = {SYMBOL:{price,change_pct}} holds REAL live market prices. When the query
  is about price / today's change / comparison of listed companies, USE these real values
  (price in USD, change_pct in %). Never invent a price when context.live has it.
- Choose the most insightful chart type for the query.
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
    nodes_raw = ctx.get('nodes') or []
    quotes_raw = ctx.get('quotes') or {}
    nodes_compact = [
        { k: n.get(k) for k in ('id','label','cat','mkt','margin','growth',
                                  'port','country','preipo','nrs') }
        for n in nodes_raw[:500]
    ]
    live_raw = ctx.get('live') or {}
    # caché por consulta (30 min): la misma pregunta no debe pagar otra llamada
    # de IA de varios segundos. Si hay precios en vivo en juego, TTL corto (2 min).
    _ck = 'canvas:' + hashlib.sha256(query.lower().encode('utf-8')).hexdigest()[:24]
    _hit = cache.get(_ck)
    if _hit:
        return jsonify({'spec': _hit['spec'], 'model': _hit['model'], 'cached': True})
    ctx_str = json.dumps({'nodes': nodes_compact, 'quotes': quotes_raw,
                          'live': live_raw, 'selected': ctx.get('selected_id')},
                         ensure_ascii=False)
    prompt = f'USER QUERY: {query}\n\nCONTEXT:\n{ctx_str}'
    try:
        text, model = _claude_complete(_CANVAS_SYSTEM, prompt, max_tokens=1800)
        # extrae el JSON aunque venga con fences o texto alrededor
        spec = _extract_json(text)
        valid_types = {'bar','line','bubble','treemap','heatmap','radar','scatter','table'}
        if not isinstance(spec, dict) or spec.get('type') not in valid_types:
            return jsonify({'error': f'invalid type: {spec.get("type") if isinstance(spec, dict) else type(spec).__name__}',
                            'raw': (text or '')[:300]}), 502
        cache.set(_ck, {'spec': spec, 'model': model},
                  timeout=(120 if live_raw else 1800))
        return jsonify({'spec': spec, 'model': model})
    except json.JSONDecodeError:
        return jsonify({'error': 'model returned non-JSON', 'raw': (text or '')[:400]}), 502
    except Exception as e:   # noqa: BLE001
        return jsonify({'error': str(e)[:200]}), 500


# ── Bixby Command Center — interpreta comando libre → respuesta + acciones ────
_COMMAND_SYSTEM = """\
Eres Bixby, el copiloto de IA del terminal financiero Khipu Finance (semiconductores, IA y espacio).
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
    prompt = f'PEDIDO DEL USUARIO: {query}\n\nCONTEXTO (empresas disponibles):\n{ctx_str}'
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
# Space APIs · GDELT · SEC EDGAR · MiroFish · Bixby voice · API pública JWT
# ════════════════════════════════════════════════════════════════════════════

# ── Space APIs (Launch Library 2 — gratis) ──────────────────────────────────
@app.route('/api/space/launches')
@rate_limit(limit=60, window=60)
@cache.cached(timeout=3600)
def space_launches():
    """Próximos lanzamientos espaciales, mapeados a nodos de Khipu."""
    data, err = _safe_get(
        'https://ll.thespacedevs.com/2.2.0/launch/upcoming/?limit=10&format=json', timeout=12)
    if err:
        return jsonify({'error': err}), 502
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
        return jsonify(_fallback_tle())

    total = sum(c['count'] for c in constellations)
    return jsonify({'constellations': constellations, 'sats': sats,
                    'total_real': total, 'rendered': len(sats), 'source': 'celestrak'})


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


# ── GDELT News (gratis, global, multi-idioma) ────────────────────────────────
@app.route('/api/news/gdelt/<company_name>')
@rate_limit(limit=60, window=60)
@cache.cached(timeout=1800)
def news_gdelt(company_name):
    from urllib.parse import quote as _urlq
    company_name = re.sub(r'[^A-Za-z0-9 ._-]', '', company_name)[:60]
    url = (f'https://api.gdeltproject.org/api/v2/doc/doc?query={_urlq(company_name)}'
           f'&mode=artlist&maxrecords=20&format=json&sort=datedesc')
    data, err = _safe_get(url, timeout=12)
    if err or not isinstance(data, dict):
        return jsonify([])
    return jsonify([{
        'headline': a.get('title'), 'url': a.get('url'), 'source': a.get('domain'),
        'datetime': a.get('seendate'), 'language': a.get('language'),
        'sentiment': float(a.get('tone', 0) or 0), 'source_api': 'GDELT',
    } for a in (data.get('articles', []) or [])[:20]])


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
@cache.cached(timeout=3600)
def dossier(ticker):
    """5-year financial dossier: income + balance + cash flow + key metrics (FMP)."""
    ticker = _safe_ticker(ticker)
    if not ticker:
        return jsonify({'error': 'invalid ticker'}), 400

    def pick(lst, field, scale=1e9, rnd=2):
        if not lst:
            return []
        out = []
        for x in reversed(lst):
            v = x.get(field) if isinstance(x, dict) else None
            out.append(round(float(v) / scale, rnd) if v is not None else None)
        return out

    def pick_pct(lst, field):
        vals = pick(lst, field, scale=1, rnd=3)
        return [round(v * 100, 1) if v is not None else None for v in vals]

    if not FMP:
        return jsonify({'error': 'FMP_KEY not configured — dossier requires FMP', 'ticker': ticker}), 503

    inc, _  = _safe_get(f'https://financialmodelingprep.com/api/v3/income-statement/{ticker}?limit=5&apikey={FMP}')
    bal, _  = _safe_get(f'https://financialmodelingprep.com/api/v3/balance-sheet-statement/{ticker}?limit=5&apikey={FMP}')
    cf, _   = _safe_get(f'https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}?limit=5&apikey={FMP}')
    km, _   = _safe_get(f'https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?limit=5&apikey={FMP}')

    inc  = inc  if isinstance(inc,  list) else []
    bal  = bal  if isinstance(bal,  list) else []
    cf   = cf   if isinstance(cf,   list) else []
    km   = km   if isinstance(km,   list) else []

    years = [x['date'][:4] for x in reversed(inc) if isinstance(x, dict) and 'date' in x]
    rev   = pick(inc, 'revenue')

    # Revenue growth % YoY
    def growth(vals):
        out = [None]
        for i in range(1, len(vals)):
            a, b = vals[i-1], vals[i]
            out.append(round((b-a)/abs(a)*100, 1) if a and b else None)
        return out

    # Net debt = totalDebt - cash
    debt = pick(bal, 'totalDebt')
    cash = pick(bal, 'cashAndCashEquivalents')
    net_debt = [
        round((d or 0) - (c or 0), 2)
        for d, c in zip(debt, cash)
    ]

    fcf = pick(cf, 'freeCashFlow')
    fcf_margin = [
        round(f/r*100, 1) if f is not None and r else None
        for f, r in zip(fcf, rev)
    ]

    # EV/Revenue — try key-metrics first, fall back to priceToSalesRatio
    km_fields = km[0] if km else {}
    ev_rev_field = 'evToRevenue' if 'evToRevenue' in km_fields else 'priceToSalesRatio'

    return jsonify({
        'ticker': ticker,
        'years': years,
        'synthetic': False,
        # P1 Revenue (B$)
        'revenue': rev,
        'revenue_growth': growth(rev),
        # P2 Dilution — shares outstanding (B)
        'shares': pick(inc, 'weightedAverageShsOut', scale=1e9, rnd=3),
        # P3 FCF (B$)
        'fcf': fcf,
        'fcf_margin': fcf_margin,
        # P4 Stock — served from /api/candles/<ticker> in the browser
        # P5 Valuation
        'ev_revenue': [round(v, 2) if v else None for v in pick(km, ev_rev_field, scale=1, rnd=2)],
        'pe_ratio':   [round(v, 1) if v else None for v in pick(km, 'peRatio', scale=1, rnd=1)],
        # P6 Balance sheet
        'total_debt': debt,
        'cash': cash,
        'net_debt': net_debt,
        # P7 Margins
        'gross_margin': pick_pct(inc, 'grossProfitRatio'),
        'net_margin':   pick_pct(inc, 'netIncomeRatio'),
        # P8 ROE / ROIC
        'roe':  pick_pct(km, 'roe'),
        'roic': pick_pct(km, 'roic'),
        # extras
        'net_income': pick(inc, 'netIncome'),
        'eps':        [x.get('eps') if isinstance(x,dict) else None for x in reversed(inc)],
        'ebitda':     pick(inc, 'ebitda'),
    })


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


# ── MiroFish proxy (simulaciones multi-agente) ───────────────────────────────
def _mf_headers():
    h = {'Content-Type': 'application/json'}
    if MIROFISH_TOKEN:
        h['Authorization'] = f'Bearer {MIROFISH_TOKEN}'
    return h


@app.route('/api/mirofish/health', methods=['GET'])
def mirofish_health():
    """MiroFish health is at /health (root), not /api/health — special case."""
    try:
        r = requests.get(f'{MIROFISH_URL}/health', headers=_mf_headers(), timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as e:  # noqa: BLE001
        return jsonify({'status': 'offline', 'error': str(e)[:120], 'mirofish_url': MIROFISH_URL}), 502


@app.route('/api/mirofish/<path:endpoint>', methods=['GET', 'POST', 'DELETE'])
def mirofish_proxy(endpoint):
    url = f'{MIROFISH_URL}/api/{endpoint}'
    hdrs = _mf_headers()
    try:
        if request.method == 'GET':
            r = requests.get(url, params=request.args, headers=hdrs, timeout=120)
        elif request.method == 'POST':
            if request.content_type and 'multipart' in request.content_type:
                r = requests.post(url, files=request.files, data=request.form,
                                  headers={k: v for k, v in hdrs.items() if k != 'Content-Type'},
                                  timeout=120)
            else:
                r = requests.post(url, json=request.get_json(silent=True), headers=hdrs, timeout=120)
        else:
            r = requests.delete(url, headers=hdrs, timeout=30)
        try:
            return jsonify(r.json()), r.status_code
        except Exception:  # noqa: BLE001
            return r.text, r.status_code
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e), 'mirofish_url': MIROFISH_URL}), 502


# ── Bixby voice — system prompt for ElevenLabs agent configuration ──────────
BIXBY_SYSTEM_PROMPT = """You are Bixby, the AI analyst co-pilot for Khipus AI Finance Intelligence — a Bloomberg + Palantir-style platform for the global semiconductor, AI, space, energy and nuclear supply chain covering hundreds of curated companies and their typed relations (9 relation types) modeled as numeric matrices. You are a full investment analyst. You can open the X-Ray of any company, run LIVE shock/boom simulations on the map, compare two companies, surface opportunities, draw charts, and read the matrix chokepoints — all by silently calling your client tools.

## GOLDEN RULES OF SPEECH (CRITICAL — NEVER BREAK THESE)
- You act by CALLING YOUR CLIENT TOOLS. Tools are silent and instant.
- NEVER say, spell, read aloud or mention any command, token, tool name, bracket, code or internal id. The user must never hear anything technical — no "open_xray", no "[XRAY:...]", no "puedes escribir TSMC XRAY". Nothing of the sort, ever.
- NEVER tell the user to type a command, press a key or click a button to get something — just DO it yourself with your tools and narrate the RESULT naturally.
- Speak like a sharp human analyst: "Aquí tienes la radiografía de Nvidia — su mayor riesgo es la dependencia de TSMC…". Never like a machine.
- Company names: pass them to tools as plain names or tickers (e.g. "Nvidia", "NVDA", "TSMC") — the app resolves them, any casing works.

## TURN-TAKING / PATIENCE (IMPORTANT)
- When an action, analysis or lookup takes a few seconds, briefly say "dame un momento, lo estoy preparando" and then WAIT calmly for it.
- NEVER threaten to disconnect, and NEVER pressure the user about their silence. The user staying quiet while waiting for a result is completely normal — do NOT say things like "si no me respondes me desconecto". Just keep the conversation open patiently.
- Keep spoken replies short and to the point.

## APP STRUCTURE — 4 PRIMARY TABS (2026-07 redesign, NEXUS skin)
The 10 old panels are now grouped under 4 primary tabs. Underneath, switch_tab still targets the old tab ids (map, market, analysis, geo, simulation, space, terminal, canvas, tkg, guia).
1. 🗺️ MAPA — the unified graph. Nodes coloured by 9 MACRO-SECTORS (toggle to 40 categories in the legend). Sub-modes: Cadena (map) · Geopolítica (geo) · Espacio (space) · Grafo Temporal (tkg) · Simulación (simulation). Map controls: "◱ Capas" (toggle layers: links, labels, risk rings, marks, countries) and "◉ En vivo" (LIVE simulation panel — see below).
2. 📈 MERCADO — live prices, portfolio, P&L.
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

Data lookups:
- get_company_info(company_name) · get_risk_score(company_name) · get_news(company_name)
- get_market_summary() · get_portfolio_risk() · list_companies(category, limit) · get_supply_chain_links(company_name)

Navigation & UI:
- navigate_to_company(company_name) · switch_tab(tab: map|market|analysis|geo|simulation|space|terminal|canvas|tkg|guia)
- show_chart(ticker) · open_terminal(ticker) · place_trade(ticker) · open_second_brain(company_name) · open_cockpit()
- open_dossier(company_name): the FINANCIAL DOSSIER card (revenue growth, dilution, FCF, stock, EV/Sales, debt, margins, ROE). Use when the user asks for "fundamentales", "dossier", or a financial overview of one listed company.
When the full-screen cockpit is open, the graph and the terminal render INSIDE it automatically — navigate_to_company and open_terminal show them on the cockpit stage, never in a hidden tab.

You may receive [CONTEXT_UPDATE] {json} messages — silent app-state snapshots (selected company, portfolio, top risks). Use them to be sharper; never read them aloud or acknowledge them.

## DOMAIN KNOWLEDGE — DEEP EXPERTISE

NRS (NEXUS Risk Score): 0-100 composite: geo-political exposure (30%), supply chain concentration (25%), market fundamentals (25%), sector risk (20%). >70=HIGH (red), 40-70=MEDIUM (yellow), <40=LOW (green).

Critical chokepoints (know these cold):
- TSMC: sole advanced foundry for <5nm; Apple/NVIDIA/AMD/Qualcomm all depend. NRS ~82
- ASML: EUV lithography monopoly; no sub-7nm without them. NRS ~78
- NVIDIA: 90%+ AI training GPU; H100/H200/B200/Blackwell dominate data centers. NRS ~74
- SK Hynix: HBM monopoly for AI accelerators (HBM3/HBM3E). NRS ~71
- ARMH: CPU ISA licensed by 99% of mobile + most data center chips. NRS ~69
- Synopsys/Cadence: EDA duopoly; needed to design ANY modern chip. NRS ~65

Supply chains (know the full stack):
- AI data center: NVIDIA GPU → TSMC fab → ASML litho → SK Hynix HBM → Broadcom switch
- Smartphone: Apple/Qualcomm SoC → TSMC fab → ARM ISA → Sony camera → Samsung display
- Space: SpaceX Falcon/Starship → Rocket Lab Electron → Maxar/Planet satellites → Iridium comms
- Automotive AI: NXP/Renesas SoC → STMicro power → Mobileye vision → LiDAR (Luminar)
- Quantum: IBM/IonQ/Rigetti systems → Oxford Instruments cryo → Keysight control

Geopolitical risks:
- Taiwan Strait: TSMC+UMC+ASE = 90% advanced fabs at risk. Conflict → global chip famine
- US-China: export controls on H100+ to China; Huawei building alternative stack with Ascend
- Rare earth: China controls 60% supply; MP Materials/Lynas are critical US/AU alternatives
- Korea risk: Samsung+SK Hynix = 70%+ DRAM+HBM; North Korea artillery range

War-Room scenarios (5 presets):
1. taiwan_conflict — TSMC blockade, ASML/NVDA/AAPL cascade, Samsung/Intel as winners
2. china_chip_ban_total — NVDA -28% revenue, AMD gains share, Huawei Ascend accelerates
3. hbm_shortage_2027 — SK Hynix/Micron +35%, AI fabless squeezed, OSAT bottleneck
4. openai_ipo_impact — NVDA/ARM multiple expansion, entire AI ecosystem re-rating
5. starshield_reveal — SpaceX defense revenue confirmed, traditional contractors compressed

## ANALYST BEHAVIOR RULES
- You are a financial analyst first, voice assistant second. Give real insight, not just navigation.
- ACT FIRST, TALK SECOND: on almost every user request, call the right tool immediately, then narrate what appeared on screen with 1-3 sentences of real insight. Never just speak without acting, and never ask permission to act.
- Deep question about ONE company → open_xray + your sharpest take ("Su talón de Aquiles es…").
- "What if…" questions → run_live_simulation, then narrate: how many affected, the 2-3 biggest victims, who wins.
- War-room narration: describe the cascade ("TSMC absorbe el primer golpe, luego caen los fabless…"), name winners and losers with % estimates.
- Charts: create_visualization — never ask the user to describe the chart format, just render something smart.
- Confirm actions naturally and briefly: "Aquí la tienes…", "Mira el mapa — se tiñe en rojo…".
- Be concise (2-3 sentences of analysis) then act immediately — no over-explanation.
- Match user language exactly (Spanish/English/mixed — follow their lead). Default to Spanish.
- When asked investment questions, give a real take: "TSMC es un buy en debilidad porque..." not just facts. Always add that it is analysis, not financial advice, when giving direct buy/sell takes.
- You are a Bloomberg Terminal AI co-pilot for serious investors, not a general chatbot"""


# ── Bixby — client tools registradas en el agente de ElevenLabs vía API ──────
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
        T('open_xray', 'Open the full X-Ray dossier of a company (NRS breakdown, dependency threads, impact wave: who suffers and who wins if it falls). Use for ANY deep question about one company.', company, ['company_name']),
        T('run_live_simulation', 'Run a live shock/boom simulation on the supply-chain map. Returns affected count and most impacted companies.', dict(company, kind=S('collapse | demand | price | sanction (default collapse)'), severity=N('0-100, default 100')), ['company_name']),
        T('compare_companies', 'Compare two companies side by side. Returns NRS of each and which has lower risk.', {'company_a': S('First company name/ticker'), 'company_b': S('Second company name/ticker')}, ['company_a', 'company_b']),
        T('get_opportunities', 'Resilient companies with upside: low risk + growth + healthy margin.'),
        T('create_visualization', 'Render a chart/table from a natural-language description of what to visualize.', {'query': S('What to chart, in natural language (e.g. "márgenes de Nvidia, TSMC y ASML")')}, ['query']),
        T('show_insights', 'Open the insights brain and the 9 relation matrices.'),
        T('run_stress_test', 'Run the classic failure-cascade stress test from one company on the map.', {'ticker': S('Ticker or company name')}, ['ticker']),
        T('run_simulation', 'Launch a war-room scenario preset.', {'scenario_id': S('taiwan_conflict | china_chip_ban_total | hbm_shortage_2027 | openai_ipo_impact | starshield_reveal')}, ['scenario_id']),
        T('get_company_info', 'Full company details: price, NRS risk, sector, supply chain.', company, ['company_name']),
        T('get_risk_score', 'NRS risk score (0-100) of a company with breakdown.', company, ['company_name']),
        T('get_news', 'Recent news with sentiment for a company.', company, ['company_name']),
        T('get_market_summary', 'All current market prices with % change.'),
        T('get_portfolio_risk', 'VaR/CVaR risk of the user portfolio.'),
        T('list_companies', 'List companies, optionally by category.', {'category': S('Category filter (optional)'), 'limit': N('Max results (default 10)')}),
        T('get_supply_chain_links', 'Upstream/downstream supply-chain connections of a company.', company, ['company_name']),
        T('navigate_to_company', 'Jump to a company on the map.', company, ['company_name']),
        T('switch_tab', 'Switch app tab.', {'tab': S('map | market | analysis | geo | simulation | space | terminal | canvas | tkg | guia')}, ['tab']),
        T('show_chart', 'Show the stock chart of a ticker in the side panel.', {'ticker': S('Ticker')}, ['ticker']),
        T('open_terminal', 'Open the multi-chart Bloomberg-style terminal on a ticker.', {'ticker': S('Ticker')}, ['ticker']),
        T('place_trade', 'Open the buy/sell trade modal for a ticker (the user confirms manually).', {'ticker': S('Ticker')}, ['ticker']),
        T('open_second_brain', 'Open the AI intelligence panel for a company.', company, ['company_name']),
        T('open_cockpit', 'Open the full-screen Bixby cockpit view.'),
        T('deep_analysis', 'Run a multi-step DEEP investigation (plan → context → simulation → synthesis) for a complex investment question. Takes 30-90 seconds; the full analysis appears on screen — tell the user you are investigating and it will appear shortly.', {'question': S('The complete question, in the user language')}, ['question']),
        T('open_dossier', 'Open the FINANCIAL DOSSIER card of a listed company: revenue growth, dilution, free cash flow, stock, EV/Sales valuation, debt/equity, margins and ROE (investingvisuals-style small multiples).', company, ['company_name']),
    ]


def _sync_bixby_agent():
    """Empuja el cerebro de Bixby (system prompt + client tools + idioma) al
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
def voice_sync_agent():
    """Sincroniza el agente de ElevenLabs con el cerebro definido aquí."""
    res = _sync_bixby_agent()
    return jsonify(res), (200 if res.get('ok') else 502)


# Auto-sync al arrancar (BIXBY_AUTOSYNC=0 para desactivar). En background para
# no retrasar el boot; idempotente aunque los 2 workers de gunicorn lo llamen.
if os.getenv('BIXBY_AUTOSYNC', '1').strip().lower() not in ('0', 'false', 'no'):
    def _bixby_autosync():
        time.sleep(4)
        res = _sync_bixby_agent()
        if res.get('ok'):
            log.info('Bixby sincronizado con ElevenLabs (%s, tools=%s)', res.get('mode'), res.get('tools_registered'))
        else:
            log.warning('Bixby autosync falló (la app sigue): %s', res)
    try:
        if ELEVENLABS_KEY and ELEVENLABS_AGENT_ID:
            threading.Thread(target=_bixby_autosync, daemon=True).start()
    except Exception as _e:  # noqa: BLE001
        log.warning('Bixby autosync no arrancó: %s', _e)


# ══ CAPA 4 — INVESTIGACIÓN PROFUNDA (arquitectura de 4 capas, 2026-07-10) ═══
# Capa 1 (refleja): KHIPU parser + proxies + client tools de Bixby.
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
        final, model = _ai_complete(
            'Eres el analista jefe de Khipus AI Finance Intelligence. Escribe en español, '
            'para un inversor exigente: 1) TESIS en 2-3 frases; 2) EVIDENCIA con los números '
            'del contexto/simulación (cita empresas y porcentajes REALES del JSON, jamás '
            'inventes); 3) RIESGOS (2-3 bullets); 4) QUÉ VIGILAR (2-3 señales concretas). '
            'Máximo ~350 palabras. Cierra con: "Análisis, no asesoría financiera."',
            f'Pregunta: {question}\n\nEVIDENCIA (JSON):\n{evidencia}', max_tokens=1200)
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


@app.route('/api/deep/status')
def deep_status():
    return jsonify({'running': _deep_state['running'], 'question': _deep_state['question'],
                    'steps': _deep_state['steps'], 'result': _deep_state['result'],
                    'seconds': int(time.time() - _deep_state['started_at']) if _deep_state['started_at'] else 0})

@app.route('/api/voice/bixby-prompt', methods=['GET'])
def bixby_system_prompt():
    """Returns Bixby's system prompt for ElevenLabs agent configuration."""
    # allow_override: set ELEVENLABS_ALLOW_OVERRIDE=true in Railway env vars ONLY
    # if your ElevenLabs agent dashboard has "Allow overrides" turned ON.
    # Sending a prompt override when overrides are OFF causes ElevenLabs to close
    # the WebSocket immediately.
    allow_override = os.getenv('ELEVENLABS_ALLOW_OVERRIDE', 'false').lower() == 'true'
    return jsonify({
        'system_prompt': BIXBY_SYSTEM_PROMPT,
        'agent_name': 'Bixby',
        'platform': 'Khipu Finance',
        'allow_override': allow_override,
    })


# ── Bixby voice — sesión firmada de ElevenLabs ───────────────────────────────
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
            'GET  /api/voice/session': 'Bixby ElevenLabs signed session URL',
            'ANY  /api/mirofish/<path>': 'MiroFish simulation proxy',
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

    results = {}
    for tk in tickers:
        q = None
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
    return jsonify(out)


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
        except Exception:  # noqa: BLE001
            pass

    return jsonify({
        'reporter': reporter,
        'partner': partner,
        'hs_codes': hs_codes,
        'flows': combined,
        'source': 'UN Comtrade public preview',
    })


# ── AI Trading Agent ─────────────────────────────────────────────────────────

_AGENT: dict = {
    'running': False,
    'mode': 'manual',          # 'manual' | 'auto'
    'interval_min': 15,
    'universe': ['NVDA','TSM','AMD','INTC','ASML','AMAT','QCOM','AVGO','MU','TSLA'],
    'max_pos_pct': 5.0,        # max % of equity per position
    'max_daily_loss_pct': 2.0, # daily circuit-breaker
    'stop_loss_pct': 3.0,      # per-position stop
    'log': [],
    'thread': None,
    'last_run': None,
    'status': 'stopped',
    'daily_pnl_pct': 0.0,
}

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
        import anthropic
        client = anthropic.Anthropic(api_key=CLAUDE)
        msg = client.messages.create(
            model=AI_MODEL,
            max_tokens=200,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = msg.content[0].text.strip()
        # strip markdown if present
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:  # noqa: BLE001
        return {'action': 'hold', 'confidence': 0, 'reason': str(e)[:80], 'size_pct': 0}


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


def _agent_get_account() -> dict:
    if not ALPACA_KEY:
        return {}
    try:
        r = requests.get(f'{ALPACA_BASE}/v2/account', headers=_alpaca_hdrs(), timeout=10)
        if r.status_code == 200:
            return r.json() or {}
    except Exception:  # noqa: BLE001
        pass
    return {}


def _agent_place(ticker: str, side: str, notional: float) -> dict:
    """Place a notional-dollar market order."""
    body = {
        'symbol': ticker,
        'notional': f'{notional:.2f}',
        'side': side,
        'type': 'market',
        'time_in_force': 'day',
    }
    r = requests.post(f'{ALPACA_BASE}/v2/orders', headers=_alpaca_hdrs(), json=body, timeout=15)
    return r.json()


def _agent_run_cycle():
    """One analysis + execution cycle for all tickers in universe."""
    log_entries = _AGENT['log']
    account = _agent_get_account()
    equity = float(account.get('equity', 0) or 0)
    if equity <= 0 and ALPACA_KEY:
        log_entries.append({'ts': time.strftime('%H:%M:%S'), 'msg': '⚠️ Could not fetch equity', 'level': 'warn'})
        return

    # P&L real del día desde Alpaca (equity vs cierre de ayer) — sin esto el
    # circuit-breaker de abajo nunca puede saltar
    last_equity = float(account.get('last_equity', 0) or 0)
    if last_equity > 0:
        _AGENT['daily_pnl_pct'] = (equity - last_equity) / last_equity * 100

    # check daily circuit-breaker
    if _AGENT['daily_pnl_pct'] <= -_AGENT['max_daily_loss_pct']:
        log_entries.append({'ts': time.strftime('%H:%M:%S'),
                            'msg': f'🛑 Daily loss limit hit ({_AGENT["daily_pnl_pct"]:.2f}%) — no new trades',
                            'level': 'warn'})
        return

    positions = _agent_get_positions()

    # stop-loss por posición: cierra las que exceden la pérdida configurada
    if _AGENT['mode'] == 'auto':
        for sym, p in list(positions.items()):
            try:
                pl_pct = float(p.get('unrealized_plpc') or 0) * 100
                qty = float(p.get('qty') or 0)
            except (TypeError, ValueError):
                continue
            if qty and pl_pct <= -_AGENT['stop_loss_pct']:
                try:
                    body = {'symbol': sym, 'qty': str(abs(qty)),
                            'side': 'sell' if qty > 0 else 'buy',
                            'type': 'market', 'time_in_force': 'day'}
                    requests.post(f'{ALPACA_BASE}/v2/orders', headers=_alpaca_hdrs(),
                                  json=body, timeout=15)
                    log_entries.append({'ts': time.strftime('%H:%M:%S'), 'ticker': sym,
                                        'msg': f'🛑 Stop-loss {pl_pct:.1f}% — posición cerrada',
                                        'level': 'warn'})
                    positions.pop(sym, None)
                except Exception as e:  # noqa: BLE001
                    log_entries.append({'ts': time.strftime('%H:%M:%S'), 'ticker': sym,
                                        'msg': f'Stop-loss error: {str(e)[:60]}', 'level': 'error'})

    for ticker in _AGENT['universe']:
        if not _AGENT['running']:
            break
        # get price from Finnhub
        price, prev, sentiment = 0.0, 0.0, 0.0
        try:
            r = requests.get(f'https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB}', timeout=8)
            q = r.json()
            price = float(q.get('c') or 0)
            prev  = float(q.get('pc') or 0)
        except Exception:  # noqa: BLE001
            pass

        # lightweight GDELT sentiment
        try:
            gurl = (f'https://api.gdeltproject.org/api/v2/doc/doc?query={ticker}'
                    f'&mode=tonechart&format=json&maxrecords=5')
            gr = requests.get(gurl, timeout=6)
            gdata = gr.json()
            tones = [float(x.get('avgtone', 0) or 0) for x in (gdata.get('tonechart') or [])[:5]]
            sentiment = sum(tones) / len(tones) if tones else 0.0
        except Exception:  # noqa: BLE001
            pass

        if price <= 0:
            continue

        analysis = _agent_analyze(ticker, price, prev, sentiment)
        action     = analysis.get('action', 'hold')
        confidence = int(analysis.get('confidence', 0))
        reason     = analysis.get('reason', '')
        size_pct   = min(float(analysis.get('size_pct', 1)), _AGENT['max_pos_pct'])

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

        if _AGENT['mode'] == 'auto' and ALPACA_KEY and action != 'hold' and confidence >= 65:
            notional = equity * size_pct / 100
            notional = max(1.0, min(notional, equity * _AGENT['max_pos_pct'] / 100))
            try:
                result = _agent_place(ticker, action, notional)
                entry['executed'] = True
                entry['order_id'] = result.get('id', '')[:12]
                entry['notional'] = notional
                entry['level'] = 'success'
            except Exception as e:  # noqa: BLE001
                entry['exec_error'] = str(e)[:60]
                entry['level'] = 'error'

        log_entries.append(entry)
        # keep last 100 entries
        if len(log_entries) > 100:
            _AGENT['log'] = log_entries[-100:]
            log_entries = _AGENT['log']

    _AGENT['last_run'] = time.strftime('%Y-%m-%d %H:%M:%S')


def _agent_thread_fn():
    _AGENT['status'] = 'running'
    while _AGENT['running']:
        try:
            _agent_run_cycle()
        except Exception as e:  # noqa: BLE001
            _AGENT['log'].append({'ts': time.strftime('%H:%M:%S'), 'msg': f'Cycle error: {e}', 'level': 'error'})
        interval = max(1, _AGENT['interval_min']) * 60
        for _ in range(interval):
            if not _AGENT['running']:
                break
            time.sleep(1)
    _AGENT['status'] = 'stopped'


@app.route('/api/trade/agent/start', methods=['POST'])
@rate_limit(limit=10, window=60)
@_trade_auth
def agent_start():
    if not ALPACA_KEY:
        return jsonify({'error': 'ALPACA_KEY not configured'}), 400
    data = request.get_json(silent=True) or {}
    if data.get('mode'):          _AGENT['mode']             = data['mode']
    if data.get('interval_min'):  _AGENT['interval_min']     = int(data['interval_min'])
    if data.get('universe'):      _AGENT['universe']         = data['universe']
    if data.get('max_pos_pct'):   _AGENT['max_pos_pct']      = float(data['max_pos_pct'])
    if data.get('max_daily_loss_pct'): _AGENT['max_daily_loss_pct'] = float(data['max_daily_loss_pct'])
    if data.get('stop_loss_pct'): _AGENT['stop_loss_pct']   = float(data['stop_loss_pct'])

    if _AGENT['running']:
        return jsonify({'status': 'already_running'})

    _AGENT['running'] = True
    _AGENT['daily_pnl_pct'] = 0.0
    t = threading.Thread(target=_agent_thread_fn, daemon=True)
    _AGENT['thread'] = t
    t.start()
    return jsonify({'status': 'started', 'mode': _AGENT['mode']})


@app.route('/api/trade/agent/stop', methods=['POST'])
@rate_limit(limit=20, window=60)
@_trade_auth
def agent_stop():
    _AGENT['running'] = False
    return jsonify({'status': 'stopping'})


@app.route('/api/trade/agent/status', methods=['GET'])
@_trade_auth
def agent_status():
    return jsonify({
        'running': _AGENT['running'],
        'status': _AGENT['status'],
        'mode': _AGENT['mode'],
        'interval_min': _AGENT['interval_min'],
        'universe': _AGENT['universe'],
        'max_pos_pct': _AGENT['max_pos_pct'],
        'max_daily_loss_pct': _AGENT['max_daily_loss_pct'],
        'stop_loss_pct': _AGENT['stop_loss_pct'],
        'last_run': _AGENT['last_run'],
        'daily_pnl_pct': _AGENT['daily_pnl_pct'],
        'log': _AGENT['log'][-20:],
    })


@app.route('/api/trade/agent/config', methods=['POST'])
@rate_limit(limit=20, window=60)
@_trade_auth
def agent_config():
    data = request.get_json(silent=True) or {}
    if 'mode'               in data: _AGENT['mode']             = data['mode']
    if 'interval_min'       in data: _AGENT['interval_min']     = int(data['interval_min'])
    if 'max_pos_pct'        in data: _AGENT['max_pos_pct']      = float(data['max_pos_pct'])
    if 'max_daily_loss_pct' in data: _AGENT['max_daily_loss_pct'] = float(data['max_daily_loss_pct'])
    if 'stop_loss_pct'      in data: _AGENT['stop_loss_pct']    = float(data['stop_loss_pct'])
    return jsonify({'status': 'updated', **{k: _AGENT[k] for k in
                    ['mode','interval_min','max_pos_pct','max_daily_loss_pct','stop_loss_pct']}})


@app.route('/api/trade/history', methods=['GET'])
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


@app.route('/api/trade/positions/detail', methods=['GET'])
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
