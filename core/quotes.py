"""core/quotes.py — cotización cruda compartida (server rutas + agentes de alertas)."""
from core.config import FINNHUB
from core.http import _safe_get


def _fetch_quote_raw(ticker):
    """Cotización cruda de Finnhub para un ticker ya saneado. Devuelve
    (data, error) — reusada por la ruta HTTP y por el evaluador de alertas
    (ontology/agents.py) para no duplicar la llamada. El caller debe checar
    FINNHUB antes de llamar (aquí asumimos que la key existe)."""
    return _safe_get(f'https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB}')
