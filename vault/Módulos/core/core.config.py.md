---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/config.py"
lenguaje: "python"
lineas: 80
aliases: ["core/config.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/config.py

> Módulo · capa [[Capa Infraestructura]] · 80 líneas · `core/config.py`

## Para qué sirve

variables de entorno compartidas entre server y ontology.

## API pública

_Sin funciones ni clases públicas de nivel superior._

## Depende de

_Nada interno._

## Lo usan

- [[brokerage.service.py]] — lo importa
- [[core.ai.py]] — lo importa
- [[core.company_data.py]] — lo importa
- [[core.http.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa
- [[core.news_feed.py]] — lo importa
- [[core.providers.market.py]] — lo importa
- [[core.quotes.py]] — lo importa
- [[core.websearch.py]] — lo importa
- [[ontology.agents.py]] — lo importa
- [[research.auto_events.py]] — lo importa
- [[research.context.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 5 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV AI_MODEL_DEEP]]
- [[ENV AI_MODEL_FAST]]
- [[ENV AI_ORDER]]
- [[ENV ANTHROPIC_KEY]]
- [[ENV CLAUDE_KEY]]
- [[ENV FINNHUB_KEY]]
- [[ENV GEMINI_FALLBACK_MODEL]]
- [[ENV GEMINI_KEY]]
- [[ENV GEMINI_MODEL]]
- [[ENV GOOGLE_API_KEY]]
- [[ENV INVESTIGADOR_AUTO]]
- [[ENV INVESTIGADOR_AUTO_CUTOFF_HORAS]]
- [[ENV NVIDIA_API_KEY]]
- [[ENV NVIDIA_KEY]]
- [[ENV NVIDIA_MODEL]]
- [[ENV TAVILY_KEY]]

## Pruebas que lo cubren

- [[tests.test_investigador.py]]
- [[tests.test_overnight3_diag_bilingual.py]]
- [[tests.test_overnight_ai_routing.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_providers.py]]
- [[tests.test_quotes_live.py]]
- [[tests.test_repair_prices.py]]
