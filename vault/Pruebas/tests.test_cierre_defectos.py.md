---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_cierre_defectos.py"
lenguaje: "python"
lineas: 260
aliases: ["tests/test_cierre_defectos.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_cierre_defectos.py

> Prueba · capa [[Capa Pruebas]] · 260 líneas · `tests/test_cierre_defectos.py`

## Qué prueba

los defectos que encontró la auditoría de cierre del lote H (docs/CIERRE_INFRA.md §4) y la revisión del replay, cada uno con la prueba que fallaba antes del arreglo:

**11** funciones `test_…`.

## Cubre

- [[brokerage.service.py]]
- [[core.decisions.py]]
- [[core.governance.py]]
- [[core.identity.py]]
- [[core.ledger_api.py]]
- [[core.providers.news.py]]
- [[core.replay.py]]
- [[engine.audit.js]]
- [[engine.explain.js]]
- [[matrix.api.py]]
- [[ontology.api.py]]
- [[ontology.db.py]]
- [[ontology.governance_models.py]]
- [[ontology.history_models.py]]
- [[ontology.ledger_models.py]]
- [[ontology.sqltypes.py]]
- [[research.outcomes.py]]

## Rutas HTTP que llama

7 rutas, de los grupos: [[API ledger]], [[API matrix]], [[API ontology]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV SECRET_KEY]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (h) — PASO 24 - REPETIR DECISIONES (replay), IMPLEMENTACIONES RETENIDAS]]
