---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/news_facts.py"
lenguaje: "python"
lineas: 340
aliases: ["ontology/news_facts.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/news_facts.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 340 líneas · `ontology/news_facts.py`

## Para qué sirve

LA ONTOLOGÍA SE ACTUALIZA SOLA desde las noticias (2026-11-21, pedido de Fabrizio: «que el agente de noticias vaya dotando de nuevos hechos y otro agente los incorpore, si no, ¿de qué sirve?»).

## API pública

- `enabled()` _(línea 68)_
- `daily_cap()` _(línea 72)_
- `confidence(kind, trust, n_outlets)` — Confianza CALCULADA: base por tipo + fuente (0-3) + corroboración. Un agregador solo (trust 1) queda bajo el umbral de aplicación … _(línea 137)_
- `pick_companies(session, n=…)` _(línea 146)_
- `fetch_news(company, days=…, getter=…)` _(línea 161)_
- `extract(company, news, ai_json=…)` — Titulares → hechos crudos (lo que dijo el modelo pequeño). Nunca lanza. _(línea 184)_
- `curate(session, company, news, facts, resolver=…)` — Hechos crudos → propuestas listas para run_agents (o nada). Devuelve (propuestas, descartes). _(línea 235)_
- clase `LectorHechos` _(línea 306)_

**Internas** (empiezan con `_`): `_has_ai`, `_take_budget`, `_norm`, `_strip_suffix`, `_mentions`, `_digits`, `_amount_in`, `_trust`, `_resolve`, `_link_exists`, `_already_proposed`

## Depende de

- [[core.ai.py]] — importa `ai`
- [[core.ai_usage.py]] — importa `ai_context`
- [[core.config.py]] — importa `config`
- [[core.entities.py]] — importa `UMBRAL_ESCRITURA`, `resolve`
- [[core.model_router.py]] — importa `models`
- [[core.news_feed.py]] — importa `_company_news`
- [[ontology.models.py]] — importa `LinkRecord`, `ObjectRecord`, `ProposedAction`
- [[ontology.provenance.py]] — importa `guess_kind`, `source_trust`

## Lo usan

- [[ontology.agents.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV ONTOLOGY_NEWS_DAILY]]
- [[ENV ONTOLOGY_NEWS_FACTS]]

## Pruebas que lo cubren

- [[tests.test_news_facts.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
