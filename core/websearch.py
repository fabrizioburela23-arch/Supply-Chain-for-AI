"""core/websearch.py — búsqueda web real para investigación autónoma.

Envuelve Tavily (TAVILY_KEY). Nunca lanza — el caller (agente) debe seguir
funcionando sin resultados, igual que _safe_get(). `include_answer: False` es
deliberado: Tavily puede devolver un resumen ya "cocinado", pero eso
reintroduce una caja negra no citable — queremos snippets crudos con URL para
que la síntesis (y la cita) las haga la IA y sean verificables línea por línea.
Interfaz chica a propósito: cambiar de proveedor (Brave/Exa) no toca al agente.
"""
import requests

from core.config import HTTP_TIMEOUT, TAVILY_KEY


def _web_search_available():
    if TAVILY_KEY:
        return True
    try:                       # 2026-11-04: sin Tavily, la búsqueda web de Claude (misma ANTHROPIC_KEY)
        from core.ai import claude_web_available
        return claude_web_available()
    except Exception:  # noqa: BLE001
        return False


def _claude_search(query, max_results=5):
    """Respaldo sin Tavily: web_search de Anthropic. Cada resultado es un TRAMO CITADO (cited_text) con su URL, no un
    resumen sin fuente. Nunca lanza."""
    try:
        from core.ai import claude_web
        out = claude_web(query=query, max_uses=3)
    except Exception:  # noqa: BLE001
        return []
    res = [{'title': c.get('title') or c['url'], 'url': c['url'], 'content': c.get('cited_text') or '',
            'score': None, 'published_date': None} for c in out.get('citations') or []]
    return res[:max_results]


def web_search(query, max_results=5, search_depth='advanced', include_domains=None):
    """-> list[{title,url,content,score,published_date}] o [] si falla/sin key."""
    if not TAVILY_KEY:
        return _claude_search(query, max_results)
    try:
        r = requests.post('https://api.tavily.com/search', json={
            'api_key': TAVILY_KEY, 'query': query, 'search_depth': search_depth,
            'max_results': max_results, 'include_domains': include_domains or [],
            'include_answer': False,   # queremos snippets citables, no un resumen
        }, timeout=HTTP_TIMEOUT * 2)   # la investigación tolera más latencia que una quote
        if not r.ok:
            return []
        data = r.json() or {}
        return [{'title': x.get('title', ''), 'url': x.get('url', ''),
                 'content': (x.get('content') or '')[:2000],
                 'score': x.get('score'), 'published_date': x.get('published_date')}
                for x in (data.get('results') or [])[:max_results]]
    except Exception:  # noqa: BLE001
        return []
