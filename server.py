"""
server.py — Del Silicio a la IA v8
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
import logging
import requests
from datetime import date, timedelta
from flask import Flask, jsonify, send_file, request
from flask_caching import Cache

# --- Config ---
from dotenv import load_dotenv
load_dotenv()  # Lee .env: FINNHUB_KEY, FMP_KEY, CLAUDE_KEY, MARKETSTACK_KEY, AI_MODEL

app = Flask(__name__)
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # 5 min por defecto
cache = Cache(app)

logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(message)s')
log = logging.getLogger('eco')

FINNHUB  = os.getenv('FINNHUB_KEY', '')
FMP      = os.getenv('FMP_KEY', '')
CLAUDE   = os.getenv('CLAUDE_KEY', '')
MSTACK   = os.getenv('MARKETSTACK_KEY', '')
# Modelo de Claude para los análisis. Haiku 4.5 es barato y rápido (~$0.001/análisis);
# sube a claude-opus-4-8 para máxima calidad. Cambiable sin tocar código.
AI_MODEL = os.getenv('AI_MODEL', 'claude-haiku-4-5-20251001')

HTTP_TIMEOUT = 8


@app.after_request
def _log_request(resp):
    log.info('%s %s -> %s', request.method, request.path, resp.status_code)
    return resp


def _safe_get(url, timeout=HTTP_TIMEOUT):
    """GET con manejo de errores uniforme. Devuelve (json, error)."""
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code != 200:
            log.warning('upstream %s %s', r.status_code, url[:100]); return None, f'upstream {r.status_code}'
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
    return send_file('app.html')


# --- PWA: Service Worker + manifest (solo útiles en modo servidor / http) ---
@app.route('/sw.js')
def service_worker():
    resp = send_file('sw.js', mimetype='application/javascript')
    resp.headers['Service-Worker-Allowed'] = '/'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


_MANIFEST = (
    '{'
    '"name":"Del Silicio a la IA","short_name":"EcoIA","display":"standalone",'
    '"start_url":"/","scope":"/","background_color":"#F4F1EA","theme_color":"#1A1813",'
    '"description":"Inteligencia de inversion sobre la cadena de valor de la IA",'
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


# ----------------------------------------------------------------------------
# Health check / data-health
# ----------------------------------------------------------------------------
@app.route('/api/health')
def health():
    return jsonify({
        'server': True,
        'finnhub': bool(FINNHUB),
        'fmp': bool(FMP),
        'claude': bool(CLAUDE),
        'marketstack': bool(MSTACK),
        'ai_model': AI_MODEL,
        'ts': int(time.time()),
    })


# ----------------------------------------------------------------------------
# Finnhub — precios, noticias, earnings, WebSocket token
# ----------------------------------------------------------------------------
@app.route('/api/ws-token')
def ws_token():
    """El frontend necesita el token para abrir el WebSocket directamente
    (los WebSockets no se proxean fácilmente en Flask sin la lib websockets)."""
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
# FMP — fundamentales, precio objetivo, ratings, insiders
# ----------------------------------------------------------------------------
@app.route('/api/fundamentals/<ticker>')
@cache.cached(timeout=86400)  # 24h
def fundamentals(ticker):
    metrics = []
    targets = []
    ratings = []
    # P/E y EV/EBITDA: Finnhub /stock/metric disponible en plan gratuito
    if FINNHUB:
        fh, _ = _safe_get(f'https://finnhub.io/api/v1/stock/metric?symbol={ticker}&metric=all&token={FINNHUB}')
        if fh and isinstance(fh.get('metric'), dict):
            m = fh['metric']
            pe = m.get('peTTM') or m.get('peBasicExclExtraTTM')
            ev = m.get('evEbitdaTTM') or m.get('evEbitdaAnnual')
            metrics = [{'peRatio': round(float(pe), 2) if pe else None,
                        'enterpriseValueOverEBITDA': round(float(ev), 2) if ev else None}]
    # Precio objetivo y ratings: FMP (estos endpoints sí funcionan con el plan actual)
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
    return jsonify({'metrics': metrics, 'priceTarget': targets or [], 'ratings': ratings})


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
def ai_analyze():
    if not CLAUDE:
        return jsonify({'error': 'no CLAUDE_KEY'}), 400
    data = request.get_json(force=True, silent=True) or {}
    try:
        text, model = _claude_complete(
            data.get('system', ''),
            data.get('prompt', ''),
            int(data.get('max_tokens', 1000)),
        )
        return jsonify({'result': text, 'model': model})
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200]}), 500


@app.route('/api/ai/news-digest', methods=['POST'])
def news_digest():
    if not CLAUDE:
        return jsonify({'error': 'no CLAUDE_KEY'}), 400
    data = request.get_json(force=True, silent=True) or {}
    try:
        text, model = _claude_complete(
            data.get('system', ''),
            data.get('prompt', ''),
            int(data.get('max_tokens', 400)),
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
    data, err = _safe_get(
        f'https://api.marketstack.com/v2/eod/latest?access_key={MSTACK}&symbols={symbols}',
        timeout=12)
    if err:
        return jsonify({'error': err}), 502
    return jsonify(data)


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5050))
    print(f'🚀 Del Silicio a la IA v8 — Backend en http://0.0.0.0:{port}')
    print(f"   Finnhub:     {'✅' if FINNHUB else '❌  (configura FINNHUB_KEY en .env)'}")
    print(f"   FMP:         {'✅' if FMP else '❌  (configura FMP_KEY en .env)'}")
    print(f"   Claude:      {'✅' if CLAUDE else '❌  (configura CLAUDE_KEY en .env)'}  modelo: {AI_MODEL}")
    print(f"   Marketstack: {'✅' if MSTACK else '❌  (configura MARKETSTACK_KEY en .env)'}")
    app.run(host='0.0.0.0', port=port, debug=False)
