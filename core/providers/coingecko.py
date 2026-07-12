"""core/providers/coingecko.py — adapter de cripto (CoinGecko API v3, tier gratuito).

Normaliza al esquema unificado CryptoAsset:
  { id, symbol, name, image, price, change_24h_pct, change_7d_pct,
    market_cap, volume_24h, rank, circulating_supply, max_supply,
    ath, ath_date, atl, atl_date, description, source }

Sin API key obligatoria. Si existe COINGECKO_KEY en el entorno se envía como
x_cg_demo_api_key (sube el rate limit) — nunca hardcodear la key.
"""
import os
import re

from core.http import _safe_get

BASE = 'https://api.coingecko.com/api/v3'
_COIN_ID_RE = re.compile(r'^[a-z0-9\-]{1,60}$')


def _key_param():
    k = os.environ.get('COINGECKO_KEY', '').strip()
    return f'&x_cg_demo_api_key={k}' if k else ''


def safe_coin_id(raw):
    """Valida un id de CoinGecko ('bitcoin', 'matic-network'). None si inválido."""
    if not raw:
        return None
    c = str(raw).strip().lower()
    return c if _COIN_ID_RE.match(c) else None


def _asset_from_market_row(r):
    """Fila de /coins/markets → CryptoAsset (parcial, sin descripción)."""
    return {
        'id': r.get('id'),
        'symbol': (r.get('symbol') or '').upper(),
        'name': r.get('name'),
        'image': r.get('image'),
        'price': r.get('current_price'),
        'change_24h_pct': r.get('price_change_percentage_24h_in_currency',
                                r.get('price_change_percentage_24h')),
        'change_7d_pct': r.get('price_change_percentage_7d_in_currency'),
        'market_cap': r.get('market_cap'),
        'volume_24h': r.get('total_volume'),
        'rank': r.get('market_cap_rank'),
        'circulating_supply': r.get('circulating_supply'),
        'max_supply': r.get('max_supply'),
        'ath': r.get('ath'),
        'ath_date': r.get('ath_date'),
        'atl': r.get('atl'),
        'atl_date': r.get('atl_date'),
        'source': 'coingecko',
    }


def list_markets(per_page=100, page=1):
    """Top de mercado cripto por capitalización. → (lista de CryptoAsset, error)."""
    per_page = max(1, min(int(per_page or 100), 250))
    page = max(1, min(int(page or 1), 10))
    url = (f'{BASE}/coins/markets?vs_currency=usd&order=market_cap_desc'
           f'&per_page={per_page}&page={page}&sparkline=false'
           f'&price_change_percentage=24h,7d{_key_param()}')
    data, err = _safe_get(url, timeout=12)
    if err:
        return None, err
    if not isinstance(data, list):
        return None, 'formato inesperado'
    return [_asset_from_market_row(r) for r in data], None


def get_asset(coin_id):
    """Detalle de una moneda. → (CryptoAsset completo, error)."""
    cid = safe_coin_id(coin_id)
    if not cid:
        return None, 'id inválido'
    url = (f'{BASE}/coins/{cid}?localization=false&tickers=false&market_data=true'
           f'&community_data=false&developer_data=false&sparkline=false{_key_param()}')
    d, err = _safe_get(url, timeout=12)
    if err:
        return None, err
    md = d.get('market_data') or {}

    def usd(field):
        v = md.get(field)
        return v.get('usd') if isinstance(v, dict) else v

    desc = ((d.get('description') or {}).get('en') or '')
    desc = re.sub(r'<[^>]+>', '', desc)[:600]
    return {
        'id': d.get('id'),
        'symbol': (d.get('symbol') or '').upper(),
        'name': d.get('name'),
        'image': (d.get('image') or {}).get('small'),
        'price': usd('current_price'),
        'change_24h_pct': md.get('price_change_percentage_24h'),
        'change_7d_pct': md.get('price_change_percentage_7d'),
        'market_cap': usd('market_cap'),
        'volume_24h': usd('total_volume'),
        'rank': d.get('market_cap_rank'),
        'circulating_supply': md.get('circulating_supply'),
        'max_supply': md.get('max_supply'),
        'ath': usd('ath'),
        'ath_date': (md.get('ath_date') or {}).get('usd'),
        'atl': usd('atl'),
        'atl_date': (md.get('atl_date') or {}).get('usd'),
        'description': desc,
        'source': 'coingecko',
    }, None


def get_history(coin_id, days=90):
    """Serie de precios diarios. → ({'prices': [[ts_ms, precio], …]}, error)."""
    cid = safe_coin_id(coin_id)
    if not cid:
        return None, 'id inválido'
    days = max(1, min(int(days or 90), 365))
    url = (f'{BASE}/coins/{cid}/market_chart?vs_currency=usd&days={days}'
           f'&interval=daily{_key_param()}')
    d, err = _safe_get(url, timeout=12)
    if err:
        return None, err
    return {'prices': d.get('prices') or [], 'source': 'coingecko'}, None
