"""Precios EN VIVO por lotes (2026-10-04): core.quotes.fetch_quotes_live +
rutas /api/quote, /api/quotes, /api/quotes/live, /api/market/providers.
Sin red: el registro de proveedores se reemplaza por uno falso."""
import os
import sys
import threading
import time
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('FINNHUB_KEY', '')
os.environ.setdefault('FMP_KEY', '')
os.environ.setdefault('ANTHROPIC_KEY', '')
os.environ.setdefault('AV_KEY', '')
os.environ.setdefault('MARKETSTACK_KEY', '')

from core import quotes  # noqa: E402
from core.providers.base import make_quote  # noqa: E402


class FakeRegistry:
    """Imita ProviderRegistry.get_quote(sym) → (quote, intentos)."""

    def __init__(self, delay=0.0, missing=(), hang=None, hang_s=2.0, provider='finnhub'):
        self.delay = delay
        self.missing = set(missing)
        self.hang = hang
        self.hang_s = hang_s
        self.provider = provider
        self.calls = []
        self.threads = set()
        self._lock = threading.Lock()

    def statuses(self):
        return [{'name': self.provider, 'configured': True, 'reason': '', 'kind': 'market'}]

    def get_quote(self, sym, prefer=None):
        with self._lock:
            self.calls.append(sym)
            self.threads.add(threading.current_thread().name)
        if sym == self.hang:
            time.sleep(self.hang_s)
        elif self.delay:
            time.sleep(self.delay)
        if sym in self.missing:
            return None, [{'provider': self.provider, 'ok': False, 'error': 'sin dato'}]
        price = 100.0 + (sum(map(ord, sym)) % 50)
        q = make_quote(sym, price, prev_close=price - 1.0, provider=self.provider,
                       currency='USD', as_of=datetime.now(timezone.utc))
        return q, [{'provider': self.provider, 'ok': True}]


@pytest.fixture(autouse=True)
def _limpio():
    quotes.live_cache_clear()
    quotes.finnhub_resume()
    yield
    quotes.live_cache_clear()
    quotes.finnhub_resume()


# ── Lote: >100 tickers, en paralelo ─────────────────────────────────────────

def test_lote_de_mas_de_100_tickers_en_paralelo():
    reg = FakeRegistry(delay=0.05)
    tks = [f'T{i}' for i in range(120)]
    t0 = time.time()
    res = quotes.fetch_quotes_live(tks, registry=reg)
    dt = time.time() - t0
    assert res['n'] == 120 and len(res['quotes']) == 120
    assert len(reg.calls) == 120
    # en serie serían 120 × 0,05 s = 6 s; con 8 hilos ≈ 0,75 s
    assert dt < 3.0, f'el lote no corrió en paralelo ({dt:.2f}s)'
    assert len(reg.threads) > 1
    assert res['cached'] is False and res['providers'] == ['finnhub']


def test_tope_de_150_por_peticion():
    reg = FakeRegistry()
    res = quotes.fetch_quotes_live([f'T{i}' for i in range(200)], registry=reg)
    assert res['n'] == quotes.LIVE_MAX_TICKERS == 150
    assert len(reg.calls) == 150


def test_cache_15s_por_lote_y_por_ticker():
    reg = FakeRegistry()
    tks = ['NVDA', 'AMD', 'TSM', '7203.T']
    r1 = quotes.fetch_quotes_live(tks, registry=reg)
    n_calls = len(reg.calls)
    r2 = quotes.fetch_quotes_live(list(reversed(tks)), registry=reg)   # mismo frozenset
    assert r2['cached'] is True and len(reg.calls) == n_calls
    assert r2['quotes'].keys() == r1['quotes'].keys()
    # lote DISTINTO que se solapa: solo se pide lo que falta
    r3 = quotes.fetch_quotes_live(['NVDA', 'MU'], registry=reg)
    assert r3['cached'] is False and reg.calls[n_calls:] == ['MU']
    assert set(r3['quotes']) == {'NVDA', 'MU'}
    # TTL vencido → se vuelve a pedir
    with quotes._LIVE_LOCK:
        for k in list(quotes._LIVE_CACHE['tickers']):
            ts, row = quotes._LIVE_CACHE['tickers'][k]
            quotes._LIVE_CACHE['tickers'][k] = (ts - 20, row)
        for k in list(quotes._LIVE_CACHE['batches']):
            ts, rows = quotes._LIVE_CACHE['batches'][k]
            quotes._LIVE_CACHE['batches'][k] = (ts - 20, rows)
    before = len(reg.calls)
    quotes.fetch_quotes_live(tks, registry=reg)
    assert len(reg.calls) == before + 4


def test_contrato_json_live_numerico_provider_as_of():
    reg = FakeRegistry(provider='yahoo')
    res = quotes.fetch_quotes_live(['7203.T'], registry=reg)
    row = res['quotes']['7203.T']
    for k in ('close', 'prev', 'pct', 'live', 'provider', 'as_of', 'age_seconds', 'currency', 'converted'):
        assert k in row, k
    assert isinstance(row['live'], float) and row['live'] > 0
    assert row['live'] == row['close']
    assert row['provider'] == 'yahoo'
    assert row['pct'] == pytest.approx((row['close'] - row['prev']) / row['prev'] * 100, abs=0.01)
    assert isinstance(row['age_seconds'], int) and row['age_seconds'] >= 0
    datetime.fromisoformat(row['as_of'].replace('Z', '+00:00'))   # ISO válido
    assert 'finnhub_quota' in res and res['finnhub_quota'] is False


def test_sin_dato_no_se_inventa_y_tickers_invalidos_se_descartan():
    reg = FakeRegistry(missing={'NADA'})
    res = quotes.fetch_quotes_live(['NVDA', 'NADA', 'malo ticker!!', ''], registry=reg)
    assert set(res['quotes']) == {'NVDA'}
    assert 'NADA' not in res['quotes']
    assert 'MALO TICKER!!' not in reg.calls


def test_proveedor_colgado_no_bloquea_el_lote():
    reg = FakeRegistry(hang='LENTO', hang_s=1.5)
    t0 = time.time()
    res = quotes.fetch_quotes_live(['NVDA', 'LENTO', 'AMD'], registry=reg, deadline=0.3)
    assert time.time() - t0 < 1.2
    assert set(res['quotes']) == {'NVDA', 'AMD'}
    # al terminar, el hilo rezagado deja su fila en la caché por ticker
    time.sleep(1.6)
    res2 = quotes.fetch_quotes_live(['LENTO'], registry=reg, deadline=0.3)
    assert 'LENTO' in res2['quotes'] and reg.calls.count('LENTO') == 1


# ── Circuito 429 de Finnhub ──────────────────────────────────────────────────

def test_circuito_429_pausa_finnhub_60s(monkeypatch):
    monkeypatch.setattr(quotes, 'FINNHUB', 'key-de-prueba', raising=False)
    calls = []

    def falso_get(url, timeout=None):
        calls.append(url)
        return None, 'el proveedor respondió HTTP 429 / upstream HTTP 429'
    monkeypatch.setattr(quotes, '_safe_get', falso_get)
    assert quotes.finnhub_quota_active() is False
    data, err = quotes._fetch_quote_raw('NVDA', timeout=4)
    assert data is None and 'HTTP 429' in err
    assert quotes.finnhub_quota_active() is True
    st = quotes.finnhub_circuit_state()
    assert st['paused'] and 0 < st['seconds_left'] <= quotes.FINNHUB_PAUSE_S and st['hits'] == 1
    # con el circuito abierto NO se llama a Finnhub (no se quema más cuota)
    data, err = quotes._fetch_quote_raw('AMD')
    assert data is None and 'pausa' in err and len(calls) == 1
    quotes.finnhub_resume()
    assert quotes.finnhub_quota_active() is False


def test_circuito_abierto_cae_a_yahoo_y_lo_expone(monkeypatch):
    """Finnhub en pausa → el adapter devuelve None, la cascada sigue con Yahoo
    y /api/quotes/live marca finnhub_quota: true."""
    from core.providers.market import FinnhubProvider
    monkeypatch.setattr('core.config.FINNHUB', 'key-de-prueba', raising=False)
    monkeypatch.setattr(quotes, 'FINNHUB', 'key-de-prueba', raising=False)
    monkeypatch.setattr(quotes, '_safe_get', lambda url, timeout=None: (None, 'upstream HTTP 429'))
    quotes.finnhub_pause()
    assert FinnhubProvider().get_quote('NVDA') is None
    assert 'pausa' in FinnhubProvider().status().reason
    reg = FakeRegistry(provider='yahoo')
    res = quotes.fetch_quotes_live(['NVDA'], registry=reg)
    assert res['finnhub_quota'] is True and res['quotes']['NVDA']['provider'] == 'yahoo'


# ── Yahoo: hora real del precio ──────────────────────────────────────────────

def test_yahoo_usa_la_hora_real_del_precio(monkeypatch):
    from core.providers.market import YahooProvider
    ts = int(datetime(2026, 10, 2, 20, 0, tzinfo=timezone.utc).timestamp())
    monkeypatch.setattr(quotes, 'fetch_quote_intl', lambda sym, timeout=6: {
        'close': 10.0, 'prev': 9.5, 'live': 10.2, 'pct': 7.37, 'vol': 100,
        'currency': 'JPY', 'converted': True, 'ts': ts, 'market_state': 'CLOSED'})
    q = YahooProvider().get_quote('7203.T')
    assert q['as_of'].startswith('2026-10-02T20:00:00')
    assert q['age_seconds'] > 3600 and q['market_state'] == 'CLOSED'
    assert q['converted'] is True and q['currency'] == 'JPY'
    row = quotes.live_row_from_quote(q)
    assert row['live'] == 10.2 and row['market_state'] == 'CLOSED'


def test_fetch_quote_intl_incluye_ts_y_market_state(monkeypatch):
    class R:
        def json(self):
            return {'chart': {'result': [{
                'meta': {'currency': 'USD', 'regularMarketPrice': 12.5, 'regularMarketTime': 1790000000,
                         'marketState': 'REGULAR', 'regularMarketVolume': 5},
                'indicators': {'quote': [{'close': [11.0, 12.0]}]}}]}}
    monkeypatch.setattr(quotes._requests, 'get', lambda *a, **k: R())
    quotes._INTL_CACHE.clear()
    q = quotes.fetch_quote_intl('ZZZTEST')
    assert q['ts'] == 1790000000 and q['market_state'] == 'REGULAR' and q['live'] == 12.5


# ── Rutas HTTP ───────────────────────────────────────────────────────────────

@pytest.fixture
def client(monkeypatch):
    import server
    reg = FakeRegistry(missing={'NADA'})
    monkeypatch.setattr('core.providers.market.market_registry', lambda: reg)
    server.app.config['TESTING'] = True
    try:
        server.cache.clear()
    except Exception:  # noqa: BLE001
        pass
    with server.app.test_client() as c:
        c.reg = reg
        yield c


def test_ruta_quotes_live_contrato_y_tope(client):
    tks = [f'T{i}' for i in range(160)] + ['ADANIPORTS.NS', '4401.T']
    r = client.post('/api/quotes/live', json={'tickers': tks})
    assert r.status_code == 200
    d = r.get_json()
    assert d['n'] == 150 and d['truncated'] is True and d['max_per_request'] == 150
    assert d['requested'] == 162
    row = d['quotes']['T0']
    assert isinstance(row['live'], float) and row['provider'] == 'finnhub' and row['as_of']
    assert 'finnhub_quota' in d and 'cached' in d
    # segundo golpe: caché
    r2 = client.post('/api/quotes/live', json={'tickers': tks})
    assert r2.get_json()['cached'] is True


def test_ruta_quotes_live_cubre_bolsas_no_eeuu(client):
    r = client.post('/api/quotes/live', json={'tickers': ['ADANIPORTS.NS', '4401.T', 'NADA']})
    d = r.get_json()
    assert set(d['quotes']) == {'ADANIPORTS.NS', '4401.T'}
    assert client.reg.calls.count('NADA') == 1


def test_ruta_quotes_live_sin_tickers_400(client):
    r = client.post('/api/quotes/live', json={})
    assert r.status_code == 400 and r.content_type.startswith('application/json')


def test_ruta_quote_compatible_con_cliente_viejo(client):
    r = client.get('/api/quote/NVDA')
    assert r.status_code == 200
    d = r.get_json()
    # claves crudas de Finnhub que DataLayer.quote / X-Ray siguen leyendo…
    assert d['c'] == d['live'] and d['pc'] == d['prev'] and d['dp'] == d['pct'] and isinstance(d['t'], int)
    # …y el contrato nuevo
    assert d['provider'] == 'finnhub' and d['as_of'] and d['symbol'] == 'NVDA'


def test_ruta_quote_sin_dato_503_json(client):
    r = client.get('/api/quote/NADA')
    assert r.status_code == 503 and r.content_type.startswith('application/json')
    assert 'finnhub_quota' in r.get_json()


def test_ruta_quotes_mapa_plano(client):
    r = client.get('/api/quotes?symbols=NVDA,AMD,NADA')
    assert r.status_code == 200
    d = r.get_json()
    assert set(d) == {'NVDA', 'AMD'} and d['AMD']['c'] > 0 and d['AMD']['provider'] == 'finnhub'
    r2 = client.get('/api/quotes?tickers=NVDA')
    assert r2.status_code == 200 and 'NVDA' in r2.get_json()
    r3 = client.get('/api/quotes')
    assert r3.status_code == 400


def test_ruta_providers_expone_finnhub_quota(client):
    r = client.get('/api/market/providers')
    d = r.get_json()
    assert d['finnhub_quota'] is False and d['finnhub_circuit']['paused'] is False
    quotes.finnhub_pause()
    d2 = client.get('/api/market/providers').get_json()
    assert d2['finnhub_quota'] is True and d2['finnhub_circuit']['seconds_left'] > 0


def test_diagnostics_incluye_fmp_y_yahoo(monkeypatch):
    import server

    class R:
        ok = True
        status_code = 200

        def __init__(self, body):
            self._b = body

        def json(self):
            return self._b

    def falso_get(url, *a, **k):
        if 'financialmodelingprep' in url:
            return R([{'symbol': 'AAPL', 'companyName': 'Apple Inc.'}])
        if 'yahoo' in url:
            return R({'chart': {'result': [{'meta': {'regularMarketPrice': 180.5}}]}})
        return R({})
    monkeypatch.setattr(server.requests, 'get', falso_get)
    monkeypatch.setattr(server, 'FMP', 'fmp-key', raising=False)
    y = server._diag_yahoo()
    assert y['ok'] is True and 'NVDA' in y['detail'] and 'latency_ms' in y
    f = server._diag_fmp()
    assert f['ok'] is True and f['configured'] is True and 'Apple' in f['detail']
    monkeypatch.setattr(server, 'FMP', '', raising=False)
    assert server._diag_fmp()['configured'] is False
