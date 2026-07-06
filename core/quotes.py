"""core/quotes.py — cotización cruda compartida (server rutas + agentes de alertas)."""
from core.config import FINNHUB
from core.http import _safe_get


def _fetch_quote_raw(ticker, timeout=None):
    """Cotización cruda de Finnhub para un ticker ya saneado. Devuelve
    (data, error) — reusada por las rutas HTTP y por el evaluador de alertas
    (ontology/agents.py) para no duplicar la llamada. El caller debe checar
    FINNHUB antes de llamar (aquí asumimos que la key existe).
    timeout: los loops batch usan 4s para no colgar el request completo."""
    url = f'https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB}'
    return _safe_get(url, timeout=timeout) if timeout else _safe_get(url)
