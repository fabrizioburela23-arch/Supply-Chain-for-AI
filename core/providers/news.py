"""core/providers/news.py — Phase 1 · M3: adapter de noticias.

Hoy GDELT se consulta desde una ruta de `server.py` y el resultado se devuelve
al navegador SIN persistirse: las noticias son un passthrough, no entran al
event store, y la URL del artículo se descarta. Este adapter es el paso previo
para que M4 pueda ingerirlas como `NewsItem` con su `Source` (la procedencia
que M1 dejó lista).

Normaliza al esquema que espera la ingesta: `{title, url, published_at,
publisher, snippet, language, source_kind}`. El `source_kind` lo infiere
`ontology/provenance.guess_kind`, así que una agencia de cable y un blog
anónimo no acaban con la misma confiabilidad.
"""
import re
from datetime import datetime, timezone

from core.providers.base import NewsProvider, ProviderStatus

_GDELT = 'https://api.gdeltproject.org/api/v2/doc/doc'


def _parse_gdelt_date(raw):
    """GDELT usa 'YYYYMMDDTHHMMSSZ'. Devuelve ISO-8601 o '' (nunca inventa)."""
    if not raw:
        return ''
    s = str(raw).strip()
    m = re.match(r'^(\d{4})(\d{2})(\d{2})T?(\d{2})(\d{2})(\d{2})Z?$', s)
    if not m:
        return ''
    try:
        return datetime(*(int(g) for g in m.groups()), tzinfo=timezone.utc).isoformat()
    except ValueError:
        return ''


class GdeltProvider(NewsProvider):
    """GDELT: noticias globales y multi-idioma, sin API key."""

    name = 'gdelt'

    def status(self):
        return ProviderStatus(self.name, True, 'Sin API key (servicio público).', kind='news')

    def get_latest(self, query, limit=10):
        from core.http import _safe_get
        from urllib.parse import quote as _q

        q = (query or '').strip()
        if not q:
            return []
        limit = max(1, min(int(limit or 10), 50))
        url = (f'{_GDELT}?query={_q(q)}&mode=artlist&maxrecords={limit}'
               f'&format=json&sort=datedesc')
        data, err = _safe_get(url)
        if err or not isinstance(data, dict):
            return []

        salida = []
        for a in (data.get('articles') or [])[:limit]:
            enlace = (a.get('url') or '').strip()
            if not enlace:
                continue   # sin URL no hay procedencia posible: se descarta
            titulo = (a.get('title') or '').strip()
            try:
                from ontology.provenance import guess_kind
                kind = guess_kind(enlace)
            except Exception:  # noqa: BLE001
                kind = 'aggregator'
            salida.append({
                'title': titulo,
                'url': enlace,
                'published_at': _parse_gdelt_date(a.get('seendate')),
                'publisher': (a.get('domain') or '').strip(),
                'snippet': '',            # GDELT artlist no trae cuerpo
                'language': (a.get('language') or '').strip(),
                'source_kind': kind,
                'provider': self.name,
            })
        return salida


_news_registry = None


def news_registry():
    from core.providers.base import ProviderRegistry
    global _news_registry
    if _news_registry is None:
        _news_registry = ProviderRegistry([GdeltProvider()])
    return _news_registry
