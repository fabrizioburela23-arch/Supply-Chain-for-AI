"""core/providers/market.py — Phase 1 · M3: adapters de datos de mercado.

Envuelven la lógica que YA funcionaba (core/quotes.py) para exponerla bajo el
contrato de base.py. No reescriben nada: `core/quotes.py` ya convierte divisas
a USD con tipo de cambio en vivo y se niega a publicar un precio si no tiene
la tasa — ese criterio se conserva tal cual.

Lo que M3 añade es la NORMALIZACIÓN: misma forma de respuesta, `as_of`
explícito, y saber qué proveedor contestó.
"""
from datetime import datetime, timezone

from core.providers.base import (MarketDataProvider, ProviderRegistry,
                                 ProviderStatus, make_quote)


def _utcnow():
    return datetime.now(timezone.utc)


class FinnhubProvider(MarketDataProvider):
    """Finnhub: cotización de EE.UU. en tiempo casi real. Requiere key."""

    name = 'finnhub'

    def status(self):
        from core.config import FINNHUB
        if not FINNHUB:
            return ProviderStatus(self.name, False,
                                  'Falta FINNHUB_KEY en las variables del servidor.')
        return ProviderStatus(self.name, True)

    def get_quote(self, symbol):
        from core.config import FINNHUB
        if not FINNHUB:
            return None
        from core.http import _safe_ticker
        from core.quotes import _fetch_quote_raw

        tk = _safe_ticker(symbol)
        if not tk:
            return None
        data, err = _fetch_quote_raw(tk)
        if err or not data:
            return None
        precio = data.get('c')
        if not precio:      # Finnhub devuelve 0 para símbolos que no cubre
            return None
        # `t` es el timestamp UNIX del dato: es la frescura REAL, no la hora a
        # la que preguntamos. Sin esto la UI no puede distinguir un precio de
        # hace 5 segundos de uno del cierre de ayer.
        as_of = _utcnow()
        try:
            if data.get('t'):
                as_of = datetime.fromtimestamp(float(data['t']), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            pass
        return make_quote(tk, precio, prev_close=data.get('pc'),
                          provider=self.name, as_of=as_of)


class YahooProvider(MarketDataProvider):
    """Yahoo Finance: cualquier bolsa del mundo, SIN key. Es el que cubre los
    símbolos con sufijo (688825.SS, 7203.T, 005930.KS…) y convierte a USD."""

    name = 'yahoo'

    def status(self):
        # No necesita key; puede fallar por red, pero está siempre "configurado".
        return ProviderStatus(self.name, True, 'Sin API key (tier público).')

    def get_quote(self, symbol):
        from core.quotes import fetch_quote_intl
        q = fetch_quote_intl(symbol)
        if not q or q.get('live') is None:
            return None
        return make_quote(symbol, q.get('live'), prev_close=q.get('prev'),
                          provider=self.name, currency=q.get('currency') or 'USD',
                          converted=bool(q.get('converted')), volume=q.get('vol'),
                          as_of=_utcnow())


class CoinGeckoProvider(MarketDataProvider):
    """Cripto. Era el ÚNICO adapter que existía; ahora cumple el mismo
    contrato que los de acciones, así que la cascada es uniforme."""

    name = 'coingecko'
    kind = 'crypto'

    def status(self):
        import os
        detalle = ('Con COINGECKO_KEY (rate limit más alto).' if os.getenv('COINGECKO_KEY')
                   else 'Sin API key (tier gratuito).')
        return ProviderStatus(self.name, True, detalle, kind=self.kind)

    def get_quote(self, symbol):
        from core.providers import coingecko
        cid = coingecko.safe_coin_id(symbol)
        if not cid:
            return None
        activo = coingecko.get_asset(cid)
        if not activo or activo.get('price') is None:
            return None
        precio = activo['price']
        pct = activo.get('change_24h_pct')
        # CoinGecko da el % de 24 h, no el cierre previo: se deriva para que el
        # esquema sea uniforme, en vez de dejar un hueco.
        prev = None
        try:
            if pct not in (None, -100):
                prev = float(precio) / (1 + float(pct) / 100.0)
        except (TypeError, ValueError, ZeroDivisionError):
            prev = None
        return make_quote(cid, precio, prev_close=prev, provider=self.name,
                          volume=activo.get('volume_24h'), as_of=_utcnow())


_registry = None


def market_registry():
    """Cascada de acciones: Finnhub primero (más fresco y con timestamp real),
    Yahoo después (cubre el resto del mundo y no necesita key)."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry([FinnhubProvider(), YahooProvider()])
    return _registry


_crypto_registry = None


def crypto_registry():
    global _crypto_registry
    if _crypto_registry is None:
        _crypto_registry = ProviderRegistry([CoinGeckoProvider()])
    return _crypto_registry
