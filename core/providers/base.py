"""core/providers/base.py — Phase 1 · M3: el contrato de los proveedores.

`core/providers/__init__.py` describía este patrón desde 2026-07 y citaba este
archivo… que nunca se escribió. Resultado: solo cripto (CoinGecko) pasaba por
la capa de adapters; las acciones llamaban a Finnhub/Yahoo/FMP directamente
desde `server.py` y `core/quotes.py`, cada una con su propia forma de
respuesta. Cambiar de proveedor obligaba a tocar rutas y UI.

Aquí vive el contrato. Tres decisiones:

1. **Un esquema único (`Quote`) con `as_of`.** Hasta ahora una cotización no
   decía CUÁNDO se tomó, así que la UI no podía cumplir la regla de "no fingir
   tiempo real": si un dato trae 15 minutos de retraso, hay que enseñarlo.
   `as_of` + `age_seconds` lo hacen explícito.

2. **`status` en vez de silencio.** Cuando falta una key el proveedor NO
   devuelve None a secas ni inventa un precio: declara
   `configured=False` con el motivo. La diferencia entre "no hay dato" y "no
   está configurado" importa, y antes se perdía.

3. **Se envuelve lo que ya funciona.** Los adapters reusan `core/quotes.py`
   (que ya convierte divisas a USD y se niega a publicar un precio sin tipo de
   cambio real). M3 normaliza la forma, no reescribe la lógica probada.

`subscribe_quotes` / `subscribe` aparecen en el contrato pero levantan
NotImplementedError: hoy no hay streaming en ningún proveedor del stack, y
declarar un método que hace polling disfrazado de suscripción sería mentir
sobre la arquitectura (spec §6).
"""
from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc)


def _iso(dt=None):
    return (dt or _utcnow()).isoformat()


class ProviderStatus:
    """Si un proveedor puede usarse, y si no, POR QUÉ. 'Sin configurar' y
    'falló' son cosas distintas y la UI debe poder distinguirlas."""

    __slots__ = ('name', 'configured', 'reason', 'kind')

    def __init__(self, name, configured, reason='', kind='market'):
        self.name = name
        self.configured = bool(configured)
        self.reason = reason
        self.kind = kind

    def to_dict(self):
        return {'name': self.name, 'configured': self.configured,
                'reason': self.reason, 'kind': self.kind}

    def __repr__(self):
        return f'<ProviderStatus {self.name} configured={self.configured}>'


def make_quote(symbol, price, prev_close=None, provider='', currency='USD',
               converted=False, volume=None, as_of=None, delayed_minutes=None):
    """Esquema ÚNICO de cotización. Todo el sistema consume esto, nunca el JSON
    crudo de un proveedor.

    `as_of` es cuándo vale el dato (no cuándo lo pedimos) y `age_seconds` se
    deriva de él: es lo que permite a la UI decir 'hace 3 min' en vez de
    aparentar tiempo real."""
    if price is None:
        return None
    try:
        price = float(price)
    except (TypeError, ValueError):
        return None

    prev = None
    if prev_close is not None:
        try:
            prev = float(prev_close)
        except (TypeError, ValueError):
            prev = None

    ts = as_of or _utcnow()
    if isinstance(ts, str):
        iso = ts
        age = None
    else:
        iso = _iso(ts)
        try:
            age = max(0, int((_utcnow() - ts).total_seconds()))
        except Exception:  # noqa: BLE001
            age = None

    pct = None
    if prev:
        try:
            pct = round((price - prev) / prev * 100, 3)
        except ZeroDivisionError:
            pct = None

    return {
        'symbol': symbol,
        'price': round(price, 4),
        'prev_close': round(prev, 4) if prev is not None else None,
        'change_pct': pct,
        'currency': currency,
        'converted': bool(converted),   # True = se convirtió a USD desde otra divisa
        'volume': volume,
        'as_of': iso,
        'age_seconds': age,
        'delayed_minutes': delayed_minutes,   # retraso DECLARADO por el proveedor
        'provider': provider,
    }


class MarketDataProvider:
    """Contrato de datos de mercado. Un adapter nuevo = implementar esto;
    ni las rutas ni la UI cambian."""

    name = 'base'
    kind = 'market'

    def status(self):
        raise NotImplementedError

    def get_quote(self, symbol):
        """→ dict de make_quote(), o None si este proveedor no lo tiene."""
        raise NotImplementedError

    def get_history(self, symbol, days=90):
        """→ [{date, close}] o None."""
        return None

    def subscribe_quotes(self, symbols, on_quote):
        # Ningún proveedor del stack actual expone streaming. Llamar a esto
        # 'suscripción' haciendo polling por dentro escondería esa realidad.
        raise NotImplementedError(
            f'{self.name} no soporta streaming; usa get_quote bajo demanda')


class NewsProvider:
    """Contrato de noticias. Lo consume M4 (ingesta al grafo)."""

    name = 'base'
    kind = 'news'

    def status(self):
        raise NotImplementedError

    def get_latest(self, query, limit=10):
        """→ [{title, url, published_at, publisher, snippet}]."""
        raise NotImplementedError

    def search(self, query, limit=10):
        return self.get_latest(query, limit=limit)

    def subscribe(self, query, on_item):
        raise NotImplementedError(
            f'{self.name} no soporta streaming; usa get_latest bajo demanda')


class ProviderRegistry:
    """Cascada de proveedores: se prueban en orden y responde el primero que
    tiene el dato. La respuesta dice SIEMPRE quién contestó (`provider`), para
    que un número en pantalla se pueda rastrear hasta su origen."""

    def __init__(self, providers=None):
        self._providers = list(providers or [])

    def register(self, provider):
        self._providers.append(provider)
        return self

    def all(self):
        return list(self._providers)

    def configured(self):
        return [p for p in self._providers if p.status().configured]

    def statuses(self):
        return [p.status().to_dict() for p in self._providers]

    def get_quote(self, symbol, prefer=None):
        """Primera respuesta válida. `prefer` fuerza un proveedor al frente.
        Devuelve (quote|None, intentos[]) — los intentos explican por qué NO
        hubo dato, que es justo lo que hace falta para diagnosticar."""
        orden = self.configured()
        if prefer:
            orden.sort(key=lambda p: 0 if p.name == prefer else 1)
        intentos = []
        for p in orden:
            try:
                q = p.get_quote(symbol)
            except Exception as e:  # noqa: BLE001 — un proveedor roto no tumba la cascada
                intentos.append({'provider': p.name, 'ok': False, 'error': str(e)[:120]})
                continue
            if q:
                intentos.append({'provider': p.name, 'ok': True})
                return q, intentos
            intentos.append({'provider': p.name, 'ok': False, 'error': 'sin dato'})
        return None, intentos
