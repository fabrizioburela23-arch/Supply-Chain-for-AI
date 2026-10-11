---
tipo: "modulo"
capa: "Investigación"
ruta: "core/websearch.py"
lenguaje: "python"
lineas: 37
aliases: ["core/websearch.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# core/websearch.py

> Módulo · capa [[Capa Investigación]] · 37 líneas · `core/websearch.py`

## Para qué sirve

búsqueda web real para investigación autónoma.

## API pública

- `web_search(query, max_results=…, search_depth=…, include_domains=…)` — \-> list[{title,url,content,score,published_date}] o [] si falla/sin key. _(línea 19)_

**Internas** (empiezan con `_`): `_web_search_available`

## Depende de

- [[core.config.py]] — importa `HTTP_TIMEOUT`, `TAVILY_KEY`

## Lo usan

- [[core.khipu_chat.py]] — lo importa
- [[ontology.agents.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[research.context.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_investigador.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-08-01 — Prompt frontend+IA (Cowork) - Tracks C y D implementados]]
