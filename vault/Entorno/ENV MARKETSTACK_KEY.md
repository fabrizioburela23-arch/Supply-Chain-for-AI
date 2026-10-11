---
tipo: "variable"
capa: "Infraestructura"
nombre: "MARKETSTACK_KEY"
documentada: true
tags: ["capa/infraestructura", "tipo/variable"]
---

# MARKETSTACK_KEY

> Variable de entorno · se configura en Railway (Variables). Aquí solo el **nombre**, nunca el valor.

## La leen

- [[core.http.py]] _(en una lista de nombres, p. ej. para tapar secretos en logs)_
- [[server.py]]
- `docker-compose.yml` (despliegue)

## Pruebas que la fijan o nombran

- [[tests.test_company_data.py]]
- [[tests.test_overnight3_diag_bilingual.py]]
- [[tests.test_quotes_live.py]]
- [[tests.test_server_smoke.py]]

## ¿Está documentada en CLAUDE.md?

Sí — en la lista **Variables de entorno** de [[Doc CLAUDE]].
