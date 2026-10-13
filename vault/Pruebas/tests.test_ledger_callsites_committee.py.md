---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_ledger_callsites_committee.py"
lenguaje: "python"
lineas: 465
aliases: ["tests/test_ledger_callsites_committee.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_ledger_callsites_committee.py

> Prueba · capa [[Capa Pruebas]] · 465 líneas · `tests/test_ledger_callsites_committee.py`

## Qué prueba

INFRA_OPERATIVA §2.5 (sitios de llamada del libro), pasos 18 y 19: COMITÉ, INVESTIGACIÓN, PROPUESTAS y ALERTAS (la parte de dinero está en tests/test_ledger_callsites.py).

**10** funciones `test_…`.

## Cubre

- [[brokerage.models.py]]
- [[brokerage.service.py]]
- [[core.__init__.py]]
- [[core.ai_usage.py]]
- [[core.decision_sites.py]]
- [[core.decisions.py]]
- [[core.http.py]]
- [[core.identity.py]]
- [[core.pin.py]]
- [[ontology.agents.py]]
- [[ontology.api.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.service.py]]
- [[research.committee.py]]
- [[research.committee_api.py]]
- [[research.llm.py]]
- [[research.models.py]]
- [[research.outcomes.py]]

## Rutas HTTP que llama

6 rutas, de los grupos: [[API committee]], [[API ontology]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV RAILWAY_ENVIRONMENT]], [[ENV RAILWAY_ENVIRONMENT_NAME]], [[ENV RAILWAY_PROJECT_ID]], [[ENV SECRET_KEY]], [[ENV TRADE_PIN]]
