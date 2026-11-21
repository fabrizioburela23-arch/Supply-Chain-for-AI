---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/curation_loop.py"
lenguaje: "python"
lineas: 72
aliases: ["ontology/curation_loop.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/curation_loop.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 72 líneas · `ontology/curation_loop.py`

## Para qué sirve

el LATIDO del servidor para que la ontología se mantenga sola (2026-11-21).

## API pública

- `interval_s()` _(línea 22)_
- `enabled()` _(línea 29)_
- `beat()` — Una vuelta: pide al ciclo de la ontología que corra (si ya corre o corrió hace poco, no hace nada). _(línea 35)_
- `start()` — Idempotente. Devuelve True si arrancó el hilo ahora. _(línea 58)_
- `status()` _(línea 70)_

**Internas** (empiezan con `_`): `_loop`

## Depende de

- [[ontology.api.py]] — importa `_try_start_cycle`
- [[ontology.db.py]] — importa `ontology_available`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV KHIPU_SCHEDULER]]
- [[ENV ONTOLOGY_AUTO]]
- [[ENV ONTOLOGY_AUTO_MIN]]

## Pruebas que lo cubren

- [[tests.test_news_facts.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
