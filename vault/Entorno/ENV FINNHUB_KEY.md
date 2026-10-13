---
tipo: "variable"
capa: "Infraestructura"
nombre: "FINNHUB_KEY"
documentada: true
tags: ["capa/infraestructura", "tipo/variable"]
---

# FINNHUB_KEY

> Variable de entorno · se configura en Railway (Variables). Aquí solo el **nombre**, nunca el valor.

## La leen

- [[core.config.py]]
- [[core.http.py]] _(en una lista de nombres, p. ej. para tapar secretos en logs)_
- `docker-compose.yml` (despliegue)

## Pruebas que la fijan o nombran

- [[tests.test_company_data.py]]
- [[tests.test_ontology_alerts.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_providers.py]]
- [[tests.test_quotes_live.py]]
- [[tests.test_security.py]]
- [[tests.test_server_smoke.py]]

## ¿Está documentada en CLAUDE.md?

Sí — en la lista **Variables de entorno** de [[Doc CLAUDE]].
