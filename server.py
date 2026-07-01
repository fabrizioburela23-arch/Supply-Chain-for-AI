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
from flask import Flask, jsonify, send_file, request, abort
from flask_caching import Cache

# PyJWT es opcional: si no está instalado, la API pública /v1/* queda deshabilitada
# pero el resto del servidor (proxy de datos, voz Bixby, RAG) sigue funcionando.
try:
    import jwt
    _HAS_JWT = True
except Exception:  # noqa: BLE001
    _HAS_JWT = False

# --- Config ---
from dotenv import load_dotenv
load_dotenv()  # Lee .env: FINNHUB_KEY, FMP_KEY, CLAUDE_KEY, MARKETSTACK_KEY, AI_MODEL

app = Flask(__name__)
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # 5 min por defecto
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024  # 64 KB max request body
cache = Cache(app)

logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(message)s')
log = logging.getLogger('khipu')

FINNHUB  = os.getenv('FINNHUB_KEY', '')
FMP      = os.getenv('FMP_KEY', '')
CLAUDE   = os.getenv('ANTHROPIC_KEY') or os.getenv('CLAUDE_KEY', '')
MSTACK   = os.getenv('MARKETSTACK_KEY', '')
# Modelo de Claude para los análisis. Haiku 4.5 es barato y rápido (~$0.001/análisis);
# sube a claude-opus-4-8 para máxima calidad. Cambiable sin tocar código.
AI_MODEL = os.getenv('AI_MODEL', 'claude-haiku-4-5-20251001')

# ── Multi-proveedor de IA: alterna entre Claude, Google Gemini y NVIDIA NIM ──
# Si un canal falla (o no tiene key), pasa al siguiente automáticamente.
# NVIDIA NIM (build.nvidia.com) y Gemini tienen tier gratis útil para el MVP.
GEMINI_KEY   = os.getenv('GEMINI_KEY') or os.getenv('GOOGLE_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
NVIDIA_KEY   = os.getenv('NVIDIA_KEY') or os.getenv('NVIDIA_API_KEY', '')
NVIDIA_MODEL = os.getenv('NVIDIA_MODEL', 'meta/llama-3.1-70b-instruct')
AI_ORDER     = [p.strip() for p in os.getenv('AI_ORDER', 'claude,gemini,nvidia').split(',') if p.strip()]

# ── Grafo de Conocimiento Temporal (Graphiti/Neo4j opcional) ────────────────
NEO4J_URI      = os.getenv('NEO4J_URI', '')
NEO4J_USER     = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', '')
_TEMPORAL_FACTS = []          # store nativo en memoria (episodios ingeridos)


def _graphiti_available():
    try:
        import graphiti_core  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _temporal_mode():
    return 'neo4j' if (NEO4J_URI and NEO4J_PASSWORD and _graphiti_available()) else 'native'

# Servicios adicionales (Khipu Finance v1)
MIROFISH_URL        = os.getenv('MIROFISH_URL', 'https://mirofish-fika.up.railway.app')
MIROFISH_TOKEN      = os.getenv('MIROFISH_TOKEN', '')
ELEVENLABS_KEY      = os.getenv('ELEVENLABS_KEY', '')
ELEVENLABS_AGENT_ID = os.getenv('ELEVENLABS_AGENT_ID', '')
AV_KEY              = os.getenv('AV_KEY') or os.getenv('ALPHA_VANTAGE_KEY', '')
RAG_URL             = os.getenv('RAG_URL', 'http://localhost:5051')
SECRET_KEY          = os.getenv('SECRET_KEY', 'khipu-dev-secret-change-me')
ALPACA_KEY          = os.getenv('ALPACA_KEY', '')
ALPACA_SECRET       = os.getenv('ALPACA_SECRET', '')
ALPACA_BASE         = os.getenv('ALPACA_BASE', 'https://paper-api.alpaca.markets')

if SECRET_KEY == 'khipu-dev-secret-change-me':
    log.warning('⚠️  SECRET_KEY is default — set SECRET_KEY env var in Railway before going live')

HTTP_TIMEOUT = 8

# ── Security config (Fase 2 — endurecimiento a producto) ────────────────────
# La CSP solo se aplica cuando el server sirve la app (modo servidor). En
# standalone puro (file://) no hay server, así que estas cabeceras no afectan
# ese modo. Todas son ajustables por env para poder desactivar al instante.
CSP_ENABLED            = os.getenv('CSP_ENABLED', 'true').lower() == 'true'
CSP_REPORT_ONLY        = os.getenv('CSP_REPORT_ONLY', 'false').lower() == 'true'
ENABLE_DEBUG_ENDPOINTS = os.getenv('ENABLE_DEBUG_ENDPOINTS', 'false').lower() == 'true'

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

# Tickers válidos: letras, dígitos y los símbolos reales de mercado (., -, ^, =, :).
# Bloquea inyección de parámetros (&token=, ?, espacios) en las URLs upstream.
_TICKER_RE = re.compile(r'^[A-Za-z0-9.\-^=:]{1,15}$')

def _safe_ticker(raw):
    """Valida y normaliza un ticker. Devuelve el símbolo en mayúsculas, o None si
    es inválido. Defensa contra inyección en las llamadas a Finnhub/FMP/etc."""
    if not raw:
        return None
    t = str(raw).strip().upper()
    return t if _TICKER_RE.match(t) else None


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


def _safe_get(url, timeout=HTTP_TIMEOUT):
    """GET con manejo de errores uniforme. Devuelve (json, error)."""
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code != 200:
            return None, f'upstream {r.status_code}'
        return r.json(), None
    except requests.exceptions.Timeout:
        return None, 'timeout'
    except Exception as e:  # noqa: BLE001
        return None, str(e)[:120]


# ----------------------------------------------------------------------------
# Servir la app
# ----------------------------------------------------------------------------
@app.route('/')
def index():
    resp = send_file('app.html')
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
# Health check / data-health (extendido: incluye MiroFish, RAG, ElevenLabs)
# ----------------------------------------------------------------------------
@app.route('/api/health')
def health():
    mf_ok = rag_ok = False
    try:
        mf_ok = requests.get(f'{MIROFISH_URL}/api/health', timeout=2).ok
    except Exception:  # noqa: BLE001
        pass
    try:
        rag_ok = requests.get(f'{RAG_URL}/stats', timeout=2).ok
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
        'rag': rag_ok,
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
    for secret in (CLAUDE, ELEVENLABS_KEY, FINNHUB, FMP, MSTACK, AV_KEY, MIROFISH_TOKEN, SECRET_KEY):
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


def _diag_rag():
    t0 = time.time()
    try:
        r = requests.get(f'{RAG_URL}/stats', timeout=5)
        lat = int((time.time() - t0) * 1000)
        if r.ok:
            n = ''
            try:
                n = f" ({r.json().get('count', '?')} docs indexados)"
            except Exception:  # noqa: BLE001
                pass
            return {'configured': True, 'ok': True, 'latency_ms': lat,
                    'detail': f'Second Brain / ChromaDB vivo{n}.'}
        return {'configured': True, 'ok': False, 'latency_ms': lat,
                'detail': f'RAG respondió HTTP {r.status_code}.'}
    except Exception as e:  # noqa: BLE001
        return {'configured': bool(RAG_URL), 'ok': False, 'latency_ms': int((time.time() - t0) * 1000),
                'detail': 'RAG (ChromaDB) no responde: ' + _diag_redact(e) +
                          '. Búsqueda semántica de Bixby limitada.'}


def _diag_grafo():
    mode = _temporal_mode()
    if mode == 'native':
        return {'configured': True, 'ok': True,
                'detail': 'Grafo de Conocimiento Temporal en modo NATIVO (client-side + memoria). '
                          'Añade NEO4J_URI/USER/PASSWORD + graphiti-core para memoria persistente.'}
    # neo4j mode → probar conexión
    t0 = time.time()
    try:
        from neo4j import GraphDatabase
        drv = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        drv.verify_connectivity(); drv.close()
        return {'configured': True, 'ok': True, 'latency_ms': int((time.time() - t0) * 1000),
                'detail': 'Graphiti + Neo4j conectado — memoria temporal persistente activa.'}
    except Exception as e:  # noqa: BLE001
        return {'configured': True, 'ok': False, 'latency_ms': int((time.time() - t0) * 1000),
                'detail': 'NEO4J configurado pero no conecta: ' + _diag_redact(e)}


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
        'rag':        _diag_rag(),
        'finnhub':    _diag_finnhub(),
        'grafo':      _diag_grafo(),
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
    data, err = _safe_get(f'https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB}')
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
        data, err = _safe_get(f'https://finnhub.io/api/v1/quote?symbol={t}&token={FINNHUB}', timeout=4)
        if data:
            results[t] = data
    return jsonify(results)


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

@app.route('/api/trade/account', methods=['GET'])
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

@app.route('/api/trade/positions', methods=['GET'])
def trade_positions():
    if not ALPACA_KEY:
        return jsonify({'error': 'ALPACA_KEY not configured'}), 400
    try:
        r = requests.get(f'{ALPACA_BASE}/v2/positions',
                         headers=_alpaca_hdrs(), timeout=10)
        return jsonify(r.json()), r.status_code
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200]}), 502

@app.route('/api/trade/orders', methods=['GET'])
def trade_orders():
    if not ALPACA_KEY:
        return jsonify({'error': 'ALPACA_KEY not configured'}), 400
    try:
        r = requests.get(f'{ALPACA_BASE}/v2/orders?status=all&limit=20',
                         headers=_alpaca_hdrs(), timeout=10)
        return jsonify(r.json()), r.status_code
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200]}), 502

@app.route('/api/trade/order', methods=['POST'])
@rate_limit(20, 60)
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
# Debug temporal — ver respuesta raw de Finnhub /stock/metric
# ----------------------------------------------------------------------------
@app.route('/api/debug/fh/<ticker>')
def debug_fh(ticker):
    if not ENABLE_DEBUG_ENDPOINTS:
        abort(404)
    ticker = _safe_ticker(ticker)
    if not ticker:
        return jsonify({'error': 'invalid ticker'}), 400
    if not FINNHUB:
        return jsonify({'error': 'no key'})
    fh, err = _safe_get(f'https://finnhub.io/api/v1/stock/metric?symbol={ticker}&metric=all&token={FINNHUB}')
    return jsonify({'err': err, 'type': type(fh).__name__,
                    'keys': list(fh.keys()) if isinstance(fh, dict) else None,
                    'metric_type': type(fh.get('metric')).__name__ if isinstance(fh, dict) else None,
                    'metric_sample': dict(list(fh['metric'].items())[:5]) if isinstance(fh, dict) and isinstance(fh.get('metric'), dict) else fh})


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
# Claude — análisis de empresa / impacto de cadena / síntesis de noticias
# Un único endpoint genérico {system, prompt, max_tokens} sirve a las features 5, 6 y 9.
# ----------------------------------------------------------------------------
def _complete_claude(system, prompt, max_tokens):
    import anthropic
    client = anthropic.Anthropic(api_key=CLAUDE)
    msg = client.messages.create(
        model=AI_MODEL, max_tokens=max_tokens, system=system or '',
        messages=[{'role': 'user', 'content': prompt or ''}],
    )
    text = ''
    for block in msg.content:
        if getattr(block, 'type', None) == 'text':
            text = block.text
            break
    return text, msg.model


def _complete_gemini(system, prompt, max_tokens):
    body = {'contents': [{'parts': [{'text': (system + '\n\n' + prompt) if system else prompt}]}],
            'generationConfig': {'maxOutputTokens': max_tokens, 'temperature': 0.6}}
    r = requests.post(
        f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}',
        json=body, timeout=45)
    if not r.ok:
        raise RuntimeError(f'Gemini HTTP {r.status_code}')
    cands = (r.json() or {}).get('candidates') or []
    if not cands:
        raise RuntimeError('Gemini sin candidates')
    text = ''.join(p.get('text', '') for p in cands[0].get('content', {}).get('parts', []))
    return text, 'gemini:' + GEMINI_MODEL


def _complete_nvidia(system, prompt, max_tokens):
    body = {'model': NVIDIA_MODEL, 'max_tokens': max_tokens, 'temperature': 0.6,
            'messages': [{'role': 'system', 'content': system or ''},
                         {'role': 'user', 'content': prompt or ''}]}
    r = requests.post('https://integrate.api.nvidia.com/v1/chat/completions',
                      headers={'Authorization': f'Bearer {NVIDIA_KEY}', 'Accept': 'application/json'},
                      json=body, timeout=45)
    if not r.ok:
        raise RuntimeError(f'NVIDIA HTTP {r.status_code}')
    return (r.json()['choices'][0]['message']['content']), 'nvidia:' + NVIDIA_MODEL


_AI_PROVIDERS = {
    'claude': (lambda: bool(CLAUDE), _complete_claude),
    'gemini': (lambda: bool(GEMINI_KEY), _complete_gemini),
    'nvidia': (lambda: bool(NVIDIA_KEY), _complete_nvidia),
}


def _ai_configured():
    return any(cfg() for cfg, _ in _AI_PROVIDERS.values())


def _ai_complete(system, prompt, max_tokens=1000):
    """Intenta cada proveedor configurado en orden (AI_ORDER); si uno falla,
    pasa al siguiente. Devuelve (texto, etiqueta_modelo)."""
    errors = []
    for name in AI_ORDER:
        prov = _AI_PROVIDERS.get(name)
        if not prov or not prov[0]():
            continue
        try:
            text, model = prov[1](system, prompt, max_tokens)
            if text and text.strip():
                return text, model
            errors.append(f'{name}: respuesta vacía')
        except Exception as e:  # noqa: BLE001
            errors.append(f'{name}: {str(e)[:80]}')
    raise RuntimeError('Ningún proveedor de IA respondió. ' + ('; '.join(errors) or 'sin keys configuradas'))


# Compat: las features existentes llaman _claude_complete → ahora multi-proveedor.
def _claude_complete(system, prompt, max_tokens):
    return _ai_complete(system, prompt, max_tokens)


@app.route('/api/ai/analyze', methods=['POST'])
@rate_limit(limit=30, window=3600)   # 30 AI analyses per hour per IP
def ai_analyze():
    if not _ai_configured():
        return jsonify({'error': 'no AI provider configured (Claude/Gemini/NVIDIA)'}), 400
    data = request.get_json(force=True, silent=True) or {}
    # Clamp max_tokens to avoid runaway costs
    max_tok = min(int(data.get('max_tokens', 1000)), 2000)
    try:
        text, model = _claude_complete(
            data.get('system', ''),
            data.get('prompt', ''),
            max_tok,
        )
        return jsonify({'result': text, 'model': model})
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200]}), 500


@app.route('/api/ai/news-digest', methods=['POST'])
@rate_limit(limit=60, window=3600)   # 60 news digests per hour per IP
def news_digest():
    if not _ai_configured():
        return jsonify({'error': 'no AI provider configured (Claude/Gemini/NVIDIA)'}), 400
    data = request.get_json(force=True, silent=True) or {}
    max_tok = min(int(data.get('max_tokens', 400)), 800)
    try:
        text, model = _claude_complete(
            data.get('system', ''),
            data.get('prompt', ''),
            max_tok,
        )
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
    ctx_str = json.dumps({'nodes': nodes_compact, 'quotes': quotes_raw,
                          'live': live_raw, 'selected': ctx.get('selected_id')},
                         ensure_ascii=False)
    prompt = f'USER QUERY: {query}\n\nCONTEXT:\n{ctx_str}'
    try:
        text, model = _claude_complete(_CANVAS_SYSTEM, prompt, max_tokens=1800)
        # strip accidental markdown fences
        cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
        spec = json.loads(cleaned)
        valid_types = {'bar','line','bubble','treemap','heatmap','radar','scatter','table'}
        if spec.get('type') not in valid_types:
            return jsonify({'error': f'invalid type: {spec.get("type")}', 'raw': cleaned[:300]}), 502
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
        cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', (text or '').strip())
        data = json.loads(cleaned)
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


@app.route('/api/company_news')
@rate_limit(limit=120, window=60)
@cache.cached(timeout=1800, query_string=True)
def company_news_recent():
    """Recent news for a ticker — last 7 days, max 8 items.
    Nota: nombre distinto a company_news() (/api/news/<ticker>) para no colisionar
    el endpoint de Flask, que se deriva del nombre de la función."""
    ticker = _safe_ticker(request.args.get('symbol', ''))
    if not ticker:
        return jsonify({'error': 'invalid or missing symbol'}), 400
    if not FINNHUB:
        return jsonify({'error': 'no FINNHUB_KEY'}), 400
    from_d = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    to_d   = datetime.now().strftime('%Y-%m-%d')
    data, err = _safe_get(
        f'https://finnhub.io/api/v1/company-news?symbol={ticker}&from={from_d}&to={to_d}&token={FINNHUB}',
        timeout=8)
    if err:
        return jsonify({'error': err}), 502
    items = data if isinstance(data, list) else []
    return jsonify(items[:8])


# ════════════════════════════════════════════════════════════════════════════
# KHIPU FINANCE v1 — Backend ampliado
# Space APIs · GDELT · SEC EDGAR · MiroFish · Bixby voice · RAG · API pública JWT
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


@app.route('/api/fundamentals/<ticker>/sec')
@rate_limit(limit=60, window=60)
@cache.cached(timeout=86400)
def fundamentals_sec(ticker):
    """SEC EDGAR — datos oficiales 10-K/20-F, completamente gratis."""
    safe = _safe_ticker(ticker)
    if not safe:
        return jsonify({'error': 'invalid ticker'}), 400
    cik = _CIK_MAP.get(safe)
    if not cik:
        return jsonify({'error': f'CIK not mapped for {ticker}'}), 404
    facts, err = _safe_get(
        f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik.zfill(10)}.json', timeout=15)
    if err:
        return jsonify({'error': err}), 502
    us_gaap = facts.get('facts', {}).get('us-gaap', {})
    revenues = (us_gaap.get('RevenueFromContractWithCustomerExcludingAssessedTax', {})
                or us_gaap.get('Revenues', {}) or {})
    rev_data = revenues.get('units', {}).get('USD', [])
    annual = [r for r in rev_data if r.get('form') in ('10-K', '20-F')]
    latest_rev = max(annual, key=lambda x: x.get('end', ''), default={})
    ni_data = us_gaap.get('NetIncomeLoss', {}).get('units', {}).get('USD', [])
    latest_ni = max([r for r in ni_data if r.get('form') in ('10-K', '20-F')],
                    key=lambda x: x.get('end', ''), default={})
    return jsonify({
        'ticker': ticker, 'cik': cik, 'source': 'SEC EDGAR (official)',
        'revenue_latest': {'value': latest_rev.get('val'), 'period': latest_rev.get('end')},
        'net_income_latest': {'value': latest_ni.get('val'), 'period': latest_ni.get('end')},
        'filings_url': f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K',
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
@app.route('/api/grafo/estado')
def grafo_estado():
    mode = _temporal_mode()
    connected = False
    if mode == 'neo4j':
        try:
            # ping ligero al driver (no bloquea el arranque si falla)
            from neo4j import GraphDatabase  # graphiti trae neo4j como dependencia
            drv = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            drv.verify_connectivity()
            drv.close()
            connected = True
        except Exception:  # noqa: BLE001
            connected = False
    return jsonify({'store': mode, 'neo4j_connected': connected,
                    'facts_count': len(_TEMPORAL_FACTS)})


@app.route('/api/grafo/episodios', methods=['POST'])
@rate_limit(limit=120, window=3600)
def grafo_ingest():
    """Ingesta un hecho/episodio temporal. En modo nativo lo guarda en memoria;
    si Graphiti+Neo4j está configurado, lo persiste allí (best-effort)."""
    b = request.get_json(force=True, silent=True) or {}
    subject = str(b.get('subject', '') or b.get('name', ''))[:120]
    if not subject:
        return jsonify({'error': 'subject/name requerido'}), 400
    fact = {
        'id': 'ep_' + hashlib.md5((subject + str(b.get('valid_from', ''))).encode()).hexdigest()[:10],
        'subject': subject, 'predicate': str(b.get('predicate', ''))[:120],
        'object': str(b.get('object', ''))[:200], 'object_type': b.get('object_type', 'literal'),
        'valid_from': b.get('valid_from') or None, 'valid_until': b.get('valid_until') or None,
        'source': b.get('source', 'ingest'), 'confidence': b.get('confidence', 0.8),
        'group': b.get('group', 'g_ingest'), 'meta': b.get('meta', {}),
    }
    _TEMPORAL_FACTS.append(fact)
    if len(_TEMPORAL_FACTS) > 2000:
        del _TEMPORAL_FACTS[:len(_TEMPORAL_FACTS) - 2000]  # cap memoria
    persisted = 'native'
    if _temporal_mode() == 'neo4j':
        try:
            _graphiti_add_episode(fact)
            persisted = 'neo4j'
        except Exception:  # noqa: BLE001
            persisted = 'native (neo4j falló)'
    return jsonify({'status': 'ok', 'id': fact['id'], 'persisted': persisted})


@app.route('/api/grafo/facts')
def grafo_facts():
    subject = request.args.get('subject')
    facts = _TEMPORAL_FACTS
    if subject:
        facts = [f for f in facts if f.get('subject') == subject or f.get('object') == subject]
    return jsonify({'facts': facts[-500:], 'store': _temporal_mode()})


def _graphiti_add_episode(fact):
    """Persiste un hecho en Graphiti+Neo4j (async envuelto en sync). Opcional."""
    import asyncio
    from graphiti_core import Graphiti  # type: ignore
    from graphiti_core.nodes import EpisodeType  # type: ignore
    from datetime import datetime, timezone

    async def _run():
        g = Graphiti(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        try:
            body = f"{fact['subject']} {fact['predicate']} {fact['object']}".strip()
            await g.add_episode(
                name=fact['subject'][:80], episode_body=body,
                source_description=f"Khipus · {fact['source']}",
                reference_time=datetime.now(timezone.utc), source=EpisodeType.text,
                group_id=fact.get('group', 'khipus'),
            )
        finally:
            try:
                await g.close()
            except Exception:  # noqa: BLE001
                pass
    asyncio.run(_run())


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
BIXBY_SYSTEM_PROMPT = """You are Bixby, the AI analyst co-pilot for Khipu Finance — a Bloomberg Terminal-style intelligence platform for the global semiconductor, AI, and space supply chain covering 450+ companies. You are a full financial analyst, not just a voice assistant. You know every tab, every company, and can launch simulations, narrate War-Room results, and give deep investment insights.

## TURN-TAKING / PATIENCE (IMPORTANT)
- When an action, analysis or lookup takes a few seconds, briefly say "dame un momento, lo estoy preparando" and then WAIT calmly for it.
- NEVER threaten to disconnect, and NEVER pressure the user about their silence. The user staying quiet while waiting for a result is completely normal — do NOT say things like "si no me respondes me desconecto". Just keep the conversation open patiently.
- Keep spoken replies short and to the point.

## APP STRUCTURE — 8 TABS
1. MAP — 3D/2D supply chain graph with 450+ nodes; NRS risk scores visible on nodes
2. MARKET — Live prices, portfolio positions, P&L, watchlist, sector filter
3. ANALYSIS — Company deep-dive: NRS score, fundamentals, Second Brain AI panel, stress cascade
4. GEO — Geopolitical risk dashboard: 7 world regions, GDELT news, scenario buttons
5. SIMULATION — War-Room: MiroFish multi-agent scenarios (20 rounds), animated cascade graph, agent debate, price trajectories, winners/losers
6. SPACE — Launch calendar, SpaceX/Rocket Lab/NASA missions, satellite coverage
7. TERMINAL — Bloomberg-style multi-chart panel (2/4/6/9 charts), KHIPU> command bar
8. CANVAS IA — Natural-language chart generation (Vega-Lite via Claude); describe any chart and it appears

## COMMAND TOKENS — issue these in your responses to control the app
The user never sees these tokens. You output them silently alongside your speech.

Navigation:
- Switch tab: [TAB:map] [TAB:market] [TAB:analysis] [TAB:geo] [TAB:simulation] [TAB:space] [TAB:terminal] [TAB:canvas]
- Jump to company on graph: [NAV:company_id]  e.g. [NAV:NVIDIA] [NAV:TSMC]
- Open Second Brain panel: [SECOND_BRAIN:company_id]
- Show stock chart: [CHART:ticker]  e.g. [CHART:NVDA] [CHART:TSM]
- Open trade modal: [TRADE:ticker]  e.g. [TRADE:NVDA]
- Open Terminal tab with company chart: [TERMINAL:ticker]  e.g. [TERMINAL:NVDA]

Analysis:
- Run stress cascade: [STRESS:company_id]
- Launch simulation: [SIM:taiwan_conflict] [SIM:china_chip_ban_total] [SIM:hbm_shortage_2027] [SIM:openai_ipo_impact] [SIM:starshield_reveal]
- Show top risk companies: [NRS_TOP]
- Filter market by category: [FILTER:category]  e.g. [FILTER:gpu]
- Generate a data visualization / chart / table in Canvas IA: [CANVAS:natural-language request]
  e.g. [CANVAS:compara márgenes de NVIDIA, TSMC y ASML] · [CANVAS:top 10 empresas por riesgo NRS]
  This RENDERS the chart automatically — use it whenever the user asks to graph, compare or visualize data.

## CLIENT TOOLS — call these for live data
- navigate_to_company(company_name, ticker): jump to company on map
- get_company_info(company_name, ticker): full company details including price, NRS, supply chain
- get_risk_score(company_name, ticker): NRS score (0-100) with breakdown
- get_nrs_top10(): top 10 highest risk companies right now
- run_stress_test(ticker): simulate failure cascade from that company
- run_simulation(scenario_id): launch War-Room MiroFish geopolitical scenario
- get_portfolio_risk(): VaR/CVaR for current positions
- get_market_summary(): all current market prices with % change
- list_companies(category, limit): list companies by sector
- get_supply_chain_links(company_id, company_name): upstream/downstream connections
- get_news(company_name, ticker): recent news with sentiment score
- search_second_brain(query): search the intelligence knowledge base
- switch_tab(tab): navigate to any of the 8 tabs
- show_chart(ticker, company_name): display stock chart in map panel sidebar
- open_terminal(ticker, company_name): open Terminal tab with multi-chart Bloomberg view
- place_trade(ticker, company_name): open trade modal to buy/sell
- open_second_brain(company_id, company_name): open AI intelligence panel for company

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

## COMPANY IDs for commands
NVIDIA, TSMC, ASML, Apple, Qualcomm, AMD, Intel, Samsung, SK_Hynix, Micron, Broadcom, AMAT, KLA, Lam_Research, ARM_Holdings, MediaTek, Marvell, Synopsys, Cadence, NXP, Renesas, STMicro, Texas_Instruments, Infineon, Wolfspeed, SpaceX, Maxar_Technologies, Planet_Labs, Spire_Global, RocketLab, Iridium, Viasat, Palantir, Cloudflare, Equinix, IBM, Microsoft, Amazon, Google, Meta, Anthropic, OpenAI, Mistral_AI, Cohere, Cerebras, Groq_Inc, IonQ, Rigetti, D_Wave, MP_Materials, Mobileye, Luminar, Onsemi, Entegris

## ANALYST BEHAVIOR RULES
- You are a financial analyst first, voice assistant second. Give real insight, not just navigation.
- When asked about a company: get_company_info → give key stats → [NAV:id] to show it
- When asked about risk: get_risk_score or get_nrs_top10 → explain WHY → [NRS_TOP]
- When asked about simulation/war-room: explain the scenario briefly → [SIM:preset_id] to launch
- When narrating War-Room results: describe the cascade ("TSMC absorbs the first shock, then NVIDIA suppliers cascade..."), name winners and losers with % estimates
- When asked for Terminal view: [TAB:terminal] → [TERMINAL:ticker]
- When asked to chart/compare/visualize/tabulate data: emit [CANVAS:<what to chart>] and it renders automatically (do NOT just ask the user to describe it). e.g. [CANVAS:compara NVIDIA, TSMC y ASML por margen y riesgo]
- Always issue command tokens alongside speech — never just speak without acting
- Confirm navigation out loud: "Navegando a NVIDIA en el mapa..."
- Be concise (2-3 sentences of analysis) then act immediately — no over-explanation
- Match user language exactly (Spanish/English/mixed — follow their lead)
- When asked investment questions, give a real take: "TSMC es un buy en debilidad porque..." not just facts
- You are a Bloomberg Terminal AI co-pilot for serious investors, not a general chatbot"""

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


# ── Bixby voice — activar allow_override en el agente ElevenLabs ─────────────
@app.route('/api/voice/enable-override', methods=['POST'])
def voice_enable_override():
    """Llama a la API de ElevenLabs para activar allow_override en el agente Bixby."""
    if not ELEVENLABS_KEY:
        return jsonify({'error': 'ELEVENLABS_KEY not configured'}), 400
    agent_id = request.get_json(silent=True, force=True).get('agent_id') if request.data else None
    agent_id = agent_id or ELEVENLABS_AGENT_ID
    if not agent_id:
        return jsonify({'error': 'agent_id required'}), 400
    try:
        r = requests.patch(
            f'https://api.elevenlabs.io/v1/convai/agents/{agent_id}',
            headers={'xi-api-key': ELEVENLABS_KEY, 'Content-Type': 'application/json'},
            json={'conversation_config': {'agent': {'prompt': {'allow_override': True}}}},
            timeout=10)
        if r.ok:
            return jsonify({'success': True, 'agent_id': agent_id, 'message': 'allow_override activado'})
        return jsonify({'success': False, 'status': r.status_code, 'detail': r.text[:300]}), r.status_code
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200]}), 502


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


# ── RAG auto-indexer — index node list into Second Brain ────────────────────
@app.route('/api/rag/index-batch', methods=['POST'])
def rag_index_batch():
    """Accepts a JSON array of nodes and indexes them all into the RAG."""
    nodes = request.get_json(silent=True) or []
    if not isinstance(nodes, list):
        return jsonify({'error': 'Expected JSON array of nodes'}), 400
    indexed, errors = 0, []
    for node in nodes:
        try:
            r = requests.post(f'{RAG_URL}/index/company', json=node, timeout=30)
            if r.ok:
                indexed += 1
            else:
                errors.append({'id': node.get('id'), 'error': r.text[:100]})
        except Exception as e:  # noqa: BLE001
            errors.append({'id': node.get('id'), 'error': str(e)[:100]})
    return jsonify({'indexed': indexed, 'total': len(nodes), 'errors': errors[:10]})


# ── RAG proxy (Second Brain) ─────────────────────────────────────────────────
@app.route('/api/rag/<path:endpoint>', methods=['GET', 'POST'])
def rag_proxy(endpoint):
    url = f'{RAG_URL}/{endpoint}'
    try:
        if request.method == 'GET':
            r = requests.get(url, params=request.args, timeout=15)
        else:
            r = requests.post(url, json=request.get_json(silent=True), timeout=30)
        return jsonify(r.json()), r.status_code
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e), 'note': 'RAG server offline'}), 502


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
    try:
        import numpy as np
    except Exception:
        return jsonify({'error': 'numpy not installed on server'}), 503

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
        except Exception:
            pass
    if not returns_by_ticker:
        return jsonify({'error': 'Could not fetch historical data. Check AV_KEY on server.'}), 400

    pv = sum(p['shares'] * p['buy_price'] for p in positions.values())
    portfolio_returns = []
    for ticker, pos in positions.items():
        if ticker not in returns_by_ticker:
            continue
        weight = (pos['shares'] * pos['buy_price']) / pv
        portfolio_returns.append([x * weight for x in returns_by_ticker[ticker]])
    if not portfolio_returns:
        return jsonify({'error': 'Insufficient data'}), 400

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

    return jsonify({
        'portfolio_value': round(pv, 2),
        'var_95': {'weekly_usd': round(var_1w, 2), 'monthly_usd': round(var_1m, 2),
                   'pct': round(var_1w / pv * 100, 2)},
        'cvar_95': {'usd': round(cvar, 2), 'pct': round(cvar / pv * 100, 2)},
        'sharpe_ratio': round(sharpe, 3),
        'max_drawdown_pct': round(mdd * 100, 2),
        'risk_level': 'BAJO' if var_1w / pv < 0.03 else 'MODERADO' if var_1w / pv < 0.06 else 'ALTO',
    })


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
            'GET  /api/fundamentals/<ticker>/sec': 'SEC EDGAR fundamentals (US companies)',
            'GET  /api/voice/session': 'Bixby ElevenLabs signed session URL',
            'POST /api/rag/<path>': 'Second Brain RAG proxy',
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
        q, _ = _safe_get(f'https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB}')
        if q and q.get('c'):
            quote = {'price': q['c'], 'prev_close': q['pc'],
                     'change_pct': (q['c'] - q['pc']) / q['pc'] * 100 if q['pc'] else 0}
    return jsonify({'node_id': node_id, 'quote': quote, 'status': 'live' if quote else 'no_data'})


@app.route('/v1/risk/portfolio', methods=['POST'])
@khipu_auth('starter')
def api_portfolio_risk():
    """VaR + CVaR del portfolio del cliente (Alpha Vantage históricos)."""
    data = request.get_json(silent=True) or {}
    positions = data.get('positions', {})
    if not positions:
        return jsonify({'error': 'positions required',
                        'format': '{"NVDA":{"shares":10,"buy_price":450}}'}), 400
    try:
        import numpy as np
    except Exception:  # noqa: BLE001
        return jsonify({'error': 'numpy not installed on server'}), 503

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
        return jsonify({'error': 'Could not fetch historical data. Check ALPHA_VANTAGE_KEY.'}), 400

    pv = sum(p['shares'] * p['buy_price'] for p in positions.values())
    portfolio_returns = []
    for ticker, pos in positions.items():
        if ticker not in returns_by_ticker:
            continue
        weight = (pos['shares'] * pos['buy_price']) / pv
        portfolio_returns.append([x * weight for x in returns_by_ticker[ticker]])
    if not portfolio_returns:
        return jsonify({'error': 'Insufficient data'}), 400

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

    return jsonify({
        'portfolio_value': round(pv, 2),
        'var_95': {'weekly_usd': round(var_1w, 2), 'monthly_usd': round(var_1m, 2),
                   'pct': round(var_1w / pv * 100, 2)},
        'cvar_95': {'usd': round(cvar, 2), 'pct': round(cvar / pv * 100, 2)},
        'sharpe_ratio': round(sharpe, 3),
        'max_drawdown_pct': round(mdd * 100, 2),
        'risk_level': 'BAJO' if var_1w / pv < 0.03 else 'MODERADO' if var_1w / pv < 0.06 else 'ALTO',
    })


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
            fh, err = _safe_get(
                f'https://finnhub.io/api/v1/quote?symbol={tk}&token={FINNHUB}', timeout=4)
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


def _agent_get_equity() -> float:
    if not ALPACA_KEY:
        return 0.0
    try:
        r = requests.get(f'{ALPACA_BASE}/v2/account', headers=_alpaca_hdrs(), timeout=10)
        if r.status_code == 200:
            return float(r.json().get('equity', 0) or 0)
    except Exception:  # noqa: BLE001
        pass
    return 0.0


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
    equity = _agent_get_equity()
    if equity <= 0 and ALPACA_KEY:
        log_entries.append({'ts': time.strftime('%H:%M:%S'), 'msg': '⚠️ Could not fetch equity', 'level': 'warn'})
        return

    # check daily circuit-breaker
    if _AGENT['daily_pnl_pct'] <= -_AGENT['max_daily_loss_pct']:
        log_entries.append({'ts': time.strftime('%H:%M:%S'),
                            'msg': f'🛑 Daily loss limit hit ({_AGENT["daily_pnl_pct"]:.2f}%) — no new trades',
                            'level': 'warn'})
        return

    positions = _agent_get_positions()

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
def agent_stop():
    _AGENT['running'] = False
    return jsonify({'status': 'stopping'})


@app.route('/api/trade/agent/status', methods=['GET'])
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
