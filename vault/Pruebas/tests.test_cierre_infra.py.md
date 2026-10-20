---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_cierre_infra.py"
lenguaje: "python"
lineas: 313
aliases: ["tests/test_cierre_infra.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_cierre_infra.py

> Prueba · capa [[Capa Pruebas]] · 313 líneas · `tests/test_cierre_infra.py`

## Qué prueba

auditoría de cierre de la infraestructura operativa (docs/CIERRE_INFRA.md).

**6** funciones `test_…`.

## Cubre

- [[brokerage.models.py]]
- [[core.__init__.py]]
- [[core.decisions.py]]
- [[core.http.py]]
- [[core.replay.py]]
- [[matrix.api.py]]
- [[mcp_server.models.py]]
- [[ontology.api.py]]
- [[ontology.bulk_import.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[research.models.py]]
- [[server.py]]

## Rutas HTTP que llama

6 rutas, de los grupos: [[API ai]], [[API matrix]], [[API ontology]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV SECRET_KEY]], [[ENV TRADE_PIN]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (i) — NEO4J RETIRADO (decisión 6 de Fabrizio) — sw v264]]
- [[Sesión 2026-10-13 (h) — PASO 24 - REPETIR DECISIONES (replay), IMPLEMENTACIONES RETENIDAS]]
