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

# Servicios adicionales (Khipu Finance v1)
MIROFISH_URL        = os.getenv('MIROFISH_URL', 'https://mirofish-fika.up.railway.app')
MIROFISH_TOKEN      = os.getenv('MIROFISH_TOKEN', '')
ELEVENLABS_KEY      = os.getenv('ELEVENLABS_KEY', '')
ELEVENLABS_AGENT_ID = os.getenv('ELEVENLABS_AGENT_ID', '')
AV_KEY              = os.getenv('AV_KEY') or os.getenv('ALPHA_VANTAGE_KEY', '')
RAG_URL             = os.getenv('RAG_URL', 'http://localhost:5051')
SECRET_KEY          = os.getenv('SECRET_KEY', 'khipu-dev-secret-change-me')

if SECRET_KEY == 'khipu-dev-secret-change-me':
    log.warning('⚠️  SECRET_KEY is default — set SECRET_KEY env var in Railway before going live')

HTTP_TIMEOUT = 8

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
    # HSTS only on HTTPS (Railway)
    if request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https':
        resp.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
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
        'app': 'Khipu Finance',
        'assistant': 'Bixby',
        'finnhub': bool(FINNHUB),
        'fmp': bool(FMP),
        'claude': bool(CLAUDE),
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
@cache.cached(timeout=15, query_string=True)
def quote(ticker):
    if not FINNHUB:
        return jsonify({'error': 'no FINNHUB_KEY'}), 400
    data, err = _safe_get(f'https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB}')
    if err:
        return jsonify({'error': err}), 502
    return jsonify(data)


@app.route('/api/quotes')
@cache.cached(timeout=15, query_string=True)
def batch_quotes():
    if not FINNHUB:
        return jsonify({'error': 'no FINNHUB_KEY'}), 400
    tickers = [t for t in request.args.get('symbols', '').split(',') if t]
    results = {}
    for t in tickers[:60]:  # límite de cortesía por request
        data, err = _safe_get(f'https://finnhub.io/api/v1/quote?symbol={t}&token={FINNHUB}', timeout=4)
        if data:
            results[t] = data
    return jsonify(results)


@app.route('/api/news/<ticker>')
@cache.cached(timeout=1800)  # 30 min
def company_news(ticker):
    if not FINNHUB:
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
@cache.cached(timeout=3600)
def earnings(ticker):
    if not FINNHUB:
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
def fundamentals(ticker):
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
        log.warning('fh_debug err=%s type=%s keys=%s', fh_err, type(fh).__name__, list(fh.keys()) if isinstance(fh, dict) else 'N/A')
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
@cache.cached(timeout=86400)
def insiders(ticker):
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
def _claude_complete(system, prompt, max_tokens):
    import anthropic
    client = anthropic.Anthropic(api_key=CLAUDE)
    msg = client.messages.create(
        model=AI_MODEL,
        max_tokens=max_tokens,
        system=system or '',
        messages=[{'role': 'user', 'content': prompt or ''}],
    )
    # content es una lista de bloques; tomamos el primer bloque de texto
    text = ''
    for block in msg.content:
        if getattr(block, 'type', None) == 'text':
            text = block.text
            break
    return text, msg.model


@app.route('/api/ai/analyze', methods=['POST'])
@rate_limit(limit=30, window=3600)   # 30 AI analyses per hour per IP
def ai_analyze():
    if not CLAUDE:
        return jsonify({'error': 'no CLAUDE_KEY'}), 400
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
    if not CLAUDE:
        return jsonify({'error': 'no CLAUDE_KEY'}), 400
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


# ----------------------------------------------------------------------------
# Marketstack proxy (compatibilidad con v7)
# ----------------------------------------------------------------------------
@app.route('/api/marketstack')
@cache.cached(timeout=3600, query_string=True)
def marketstack_proxy():
    if not MSTACK:
        return jsonify({'error': 'no MARKETSTACK_KEY'}), 400
    symbols = request.args.get('symbols', '')
    from_date = request.args.get('date_from', (date.today() - timedelta(days=9)).isoformat())
    data, err = _safe_get(
        f'https://api.marketstack.com/v2/eod?access_key={MSTACK}'
        f'&symbols={symbols}&date_from={from_date}&limit=1000&sort=DESC',
        timeout=12)
    if err:
        return jsonify({'error': err}), 502
    return jsonify(data)


# ════════════════════════════════════════════════════════════════════════════
# KHIPU FINANCE v1 — Backend ampliado
# Space APIs · GDELT · SEC EDGAR · MiroFish · Bixby voice · RAG · API pública JWT
# ════════════════════════════════════════════════════════════════════════════

# ── Space APIs (Launch Library 2 — gratis) ──────────────────────────────────
@app.route('/api/space/launches')
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


# ── GDELT News (gratis, global, multi-idioma) ────────────────────────────────
@app.route('/api/news/gdelt/<company_name>')
@cache.cached(timeout=1800)
def news_gdelt(company_name):
    url = (f'https://api.gdeltproject.org/api/v2/doc/doc?query={company_name}'
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


@app.route('/api/fundamentals/<ticker>/sec')
@cache.cached(timeout=86400)
def fundamentals_sec(ticker):
    """SEC EDGAR — datos oficiales 10-K/20-F, completamente gratis."""
    cik = _CIK_MAP.get(ticker.upper())
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
BIXBY_SYSTEM_PROMPT = """You are Bixby, the AI voice assistant for Khipu Finance — a Bloomberg Terminal-style intelligence platform for the global semiconductor, AI, and space supply chain covering 450+ companies.

Your capabilities:
- Navigate to companies on the graph: use navigate_to_company({company_id})
- Run stress tests to simulate company failures: use run_stress_test({company_id})
- Launch MiroFish simulations for geopolitical scenarios: use run_simulation({scenario_text})
- Query the Second Brain RAG for company intelligence: use search_second_brain({query})
- Get portfolio risk metrics (VaR/CVaR): use get_portfolio_risk()

Key knowledge:
- Supply chain categories: fabless, foundry, equipment, memory, ASIC, photonics, AI defense, space launch, satellite, DC REITs, CDN/edge, neuromorphic, battery materials, rare earth
- Key companies: TSMC (foundry leader), NVIDIA (AI GPU), ASML (EUV monopoly), Anthropic (Claude AI), SpaceX (launch), Palantir (defense AI), Cloudflare (CDN), Equinix (DC REIT)
- NRS (NEXUS Risk Score): 0-100 composite risk score based on geo, chain, market, fundamental, concentration factors
- Always speak in the same language as the user (Spanish or English)

Be concise, analytical, and actionable. You are a financial intelligence co-pilot, not a general assistant."""

@app.route('/api/voice/bixby-prompt', methods=['GET'])
def bixby_system_prompt():
    """Returns Bixby's system prompt for ElevenLabs agent configuration."""
    return jsonify({'system_prompt': BIXBY_SYSTEM_PROMPT, 'agent_name': 'Bixby', 'platform': 'Khipu Finance'})


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
    ticker = request.args.get('ticker')
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


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5050))
    app.run(host='0.0.0.0', port=port, debug=False)
