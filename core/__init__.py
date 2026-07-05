"""core/ — helpers compartidos entre server.py (Flask) y ontology/ (agentes).

Nació para romper la dependencia circular ontology→server: los agentes de la
ontología necesitaban _ai_complete y _fetch_quote_raw y hacían `import server`
perezoso. Ahora ambos lados importan de aquí, y el futuro motor de matrices
(matrix/) también lo hará.

Módulos:
  config — variables de entorno compartidas (keys de IA, Finnhub, timeouts).
  http   — _safe_get / _safe_ticker (llamadas upstream saneadas).
  ai     — cascada multi-proveedor Claude→Gemini→NVIDIA + _extract_json.
  quotes — _fetch_quote_raw (cotización cruda Finnhub).
"""
