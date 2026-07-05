"""core/http.py — llamadas upstream saneadas (compartidas server/ontology)."""
import re

import requests

from core.config import HTTP_TIMEOUT

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
