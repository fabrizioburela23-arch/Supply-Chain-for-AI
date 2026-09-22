"""tests/test_providers.py — Phase 1 · M3: contrato de proveedores.

Lo que se protege:
  - un esquema ÚNICO de cotización, con `as_of` (spec §13: no fingir tiempo
    real; si un dato trae retraso, enseñarlo);
  - la diferencia entre "no está configurado" y "falló", que antes se perdía;
  - la cascada con respaldo, que explica por qué NO hubo dato.

No requiere red ni Postgres: los adapters se prueban con dobles.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Esquema único ───────────────────────────────────────────────────────────

def test_make_quote_normaliza_y_calcula_variacion():
    from core.providers.base import make_quote
    q = make_quote('NVDA', 120.5, prev_close=100.0, provider='finnhub')
    assert q['symbol'] == 'NVDA'
    assert q['price'] == 120.5
    assert q['prev_close'] == 100.0
    assert q['change_pct'] == 20.5
    assert q['provider'] == 'finnhub'
    assert q['currency'] == 'USD'
    assert q['as_of']            # SIEMPRE lleva marca temporal
    assert q['age_seconds'] is not None


def test_age_seconds_refleja_la_frescura_real():
    """El punto de M3: un precio de hace una hora NO debe parecer de ahora."""
    from core.providers.base import make_quote
    viejo = datetime.now(timezone.utc) - timedelta(hours=1)
    q = make_quote('NVDA', 100, as_of=viejo, provider='x')
    assert q['age_seconds'] >= 3500


def test_make_quote_sin_precio_devuelve_none():
    """Sin precio no se fabrica una cotización vacía que parezca válida."""
    from core.providers.base import make_quote
    assert make_quote('NVDA', None) is None
    assert make_quote('NVDA', 'no-es-un-numero') is None


def test_prev_close_invalido_no_inventa_variacion():
    from core.providers.base import make_quote
    q = make_quote('NVDA', 100, prev_close='basura', provider='x')
    assert q['prev_close'] is None
    assert q['change_pct'] is None      # mejor vacío que un número inventado


# ── Configurado vs. falló ───────────────────────────────────────────────────

def test_status_distingue_sin_configurar_de_fallo(monkeypatch):
    from core.providers.market import FinnhubProvider
    p = FinnhubProvider()

    monkeypatch.setattr('core.config.FINNHUB', '', raising=False)
    st = p.status()
    assert st.configured is False
    assert 'FINNHUB_KEY' in st.reason     # dice QUÉ falta, no solo que falta

    monkeypatch.setattr('core.config.FINNHUB', 'key-de-prueba', raising=False)
    assert p.status().configured is True


def test_yahoo_y_coingecko_no_necesitan_key():
    """Son los que sostienen la app cuando no hay keys configuradas."""
    from core.providers.market import CoinGeckoProvider, YahooProvider
    assert YahooProvider().status().configured is True
    assert CoinGeckoProvider().status().configured is True


# ── Cascada ─────────────────────────────────────────────────────────────────

class _Falso:
    """Doble de proveedor, para probar la cascada sin tocar la red."""
    kind = 'market'

    def __init__(self, name, quote=None, revienta=False, configurado=True):
        self.name = name
        self._q = quote
        self._revienta = revienta
        self._conf = configurado

    def status(self):
        from core.providers.base import ProviderStatus
        return ProviderStatus(self.name, self._conf, '' if self._conf else 'sin key')

    def get_quote(self, symbol):
        if self._revienta:
            raise RuntimeError('proveedor caído')
        return self._q


def test_la_cascada_usa_el_primero_que_responde():
    from core.providers.base import ProviderRegistry, make_quote
    reg = ProviderRegistry([
        _Falso('a', quote=None),
        _Falso('b', quote=make_quote('X', 10, provider='b')),
        _Falso('c', quote=make_quote('X', 99, provider='c')),
    ])
    q, intentos = reg.get_quote('X')
    assert q['provider'] == 'b'          # no llega a 'c'
    assert [i['provider'] for i in intentos] == ['a', 'b']


def test_un_proveedor_roto_no_tumba_la_cascada():
    from core.providers.base import ProviderRegistry, make_quote
    reg = ProviderRegistry([
        _Falso('roto', revienta=True),
        _Falso('bueno', quote=make_quote('X', 42, provider='bueno')),
    ])
    q, intentos = reg.get_quote('X')
    assert q['price'] == 42
    assert intentos[0]['ok'] is False and 'caído' in intentos[0]['error']


def test_prefer_pone_un_proveedor_al_frente():
    from core.providers.base import ProviderRegistry, make_quote
    reg = ProviderRegistry([
        _Falso('a', quote=make_quote('X', 1, provider='a')),
        _Falso('b', quote=make_quote('X', 2, provider='b')),
    ])
    q, _ = reg.get_quote('X', prefer='b')
    assert q['provider'] == 'b'


def test_los_no_configurados_se_saltan():
    from core.providers.base import ProviderRegistry, make_quote
    reg = ProviderRegistry([
        _Falso('sin_key', quote=make_quote('X', 1, provider='sin_key'), configurado=False),
        _Falso('ok', quote=make_quote('X', 2, provider='ok')),
    ])
    q, intentos = reg.get_quote('X')
    assert q['provider'] == 'ok'
    assert all(i['provider'] != 'sin_key' for i in intentos)


def test_sin_dato_explica_por_que():
    """Un None mudo obliga a adivinar; los intentos dicen qué pasó."""
    from core.providers.base import ProviderRegistry
    reg = ProviderRegistry([_Falso('a', quote=None), _Falso('b', quote=None)])
    q, intentos = reg.get_quote('X')
    assert q is None
    assert len(intentos) == 2
    assert all(i['ok'] is False for i in intentos)


# ── Streaming: se declara pero NO se finge ──────────────────────────────────

def test_subscribe_no_finge_streaming():
    """Ningún proveedor del stack tiene streaming. Implementarlo como polling
    disfrazado escondería la arquitectura real (spec §6)."""
    from core.providers.market import YahooProvider
    with pytest.raises(NotImplementedError):
        YahooProvider().subscribe_quotes(['NVDA'], lambda q: None)


# ── Noticias ────────────────────────────────────────────────────────────────

def test_fecha_gdelt_se_parsea_o_se_deja_vacia():
    from core.providers.news import _parse_gdelt_date
    assert _parse_gdelt_date('20260215T143000Z').startswith('2026-02-15T14:30:00')
    # formatos que no entendemos → vacío, nunca una fecha inventada
    assert _parse_gdelt_date('ayer por la tarde') == ''
    assert _parse_gdelt_date('') == ''
    assert _parse_gdelt_date(None) == ''
    assert _parse_gdelt_date('20261345T999999Z') == ''   # fecha imposible


def test_noticias_sin_url_se_descartan(monkeypatch):
    """Sin URL no hay procedencia posible, y M1 dejó claro que un hecho sin
    origen no debe entrar al grafo."""
    from core.providers.news import GdeltProvider

    falso = {'articles': [
        {'title': 'Con enlace', 'url': 'https://www.reuters.com/a',
         'seendate': '20260215T143000Z', 'domain': 'reuters.com'},
        {'title': 'Sin enlace', 'url': '', 'seendate': '20260215T143000Z'},
    ]}
    monkeypatch.setattr('core.http._safe_get', lambda *a, **k: (falso, None))
    items = GdeltProvider().get_latest('ACME')
    assert len(items) == 1
    assert items[0]['url'] == 'https://www.reuters.com/a'
    assert items[0]['source_kind'] == 'press'     # clasificada, no genérica
    assert items[0]['published_at'].startswith('2026-02-15')


def test_noticias_query_vacia_no_llama_a_la_red():
    from core.providers.news import GdeltProvider
    assert GdeltProvider().get_latest('') == []
    assert GdeltProvider().get_latest(None) == []


# ── API ─────────────────────────────────────────────────────────────────────

def test_endpoint_de_proveedores_es_honesto():
    import server
    os.environ.setdefault('SECRET_KEY', 'test')
    server.app.config['TESTING'] = True
    c = server.app.test_client()

    r = c.get('/api/market/providers')
    assert r.status_code == 200
    d = r.get_json()
    for grupo in ('market', 'crypto', 'news'):
        assert grupo in d and isinstance(d[grupo], list)
    # cada proveedor declara si está configurado y, si no, por qué
    for p in d['market']:
        assert 'name' in p and 'configured' in p
        if not p['configured']:
            assert p['reason']


def test_quote_sin_proveedores_explica_en_vez_de_404_mudo(monkeypatch):
    import server
    c = server.app.test_client()
    from core.providers.market import market_registry

    reg = market_registry()
    monkeypatch.setattr(reg, 'get_quote', lambda *a, **k: (None, [
        {'provider': 'finnhub', 'ok': False, 'error': 'sin dato'}]))
    r = c.get('/api/market/quote/NOEXISTE123')
    assert r.status_code == 404
    d = r.get_json()
    assert d['attempts'] and 'providers' in d
