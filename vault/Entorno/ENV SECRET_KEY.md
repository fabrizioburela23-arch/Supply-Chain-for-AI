---
tipo: "variable"
capa: "Infraestructura"
nombre: "SECRET_KEY"
documentada: true
tags: ["capa/infraestructura", "tipo/variable"]
---

# SECRET_KEY

> Variable de entorno · se configura en Railway (Variables). Aquí solo el **nombre**, nunca el valor.

## La leen

- [[brokerage.crypto.py]]
- [[core.decisions.py]]
- [[core.http.py]] _(en una lista de nombres, p. ej. para tapar secretos en logs)_
- [[core.identity.py]]
- [[core.pin.py]]
- [[mcp_server.oauth.py]]
- [[server.py]]
- `docker-compose.yml` (despliegue)

## Pruebas que la fijan o nombran

- [[tests.test_brokerage.py]]
- [[tests.test_cierre_defectos.py]]
- [[tests.test_cierre_infra.py]]
- [[tests.test_company_data.py]]
- [[tests.test_csp_estricta.py]]
- [[tests.test_graph_api.py]]
- [[tests.test_ingest_news.py]]
- [[tests.test_ledger_callsites.py]]
- [[tests.test_ledger_callsites_chat.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_privacy.py]]
- [[tests.test_ledger_review_fixes.py]]
- [[tests.test_neo4j_retirado.py]]
- [[tests.test_ontology_agents.py]]
- [[tests.test_ontology_alerts.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_overnight3_diag_bilingual.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_overnight_voice_server.py]]
- [[tests.test_provenance.py]]
- [[tests.test_providers.py]]
- [[tests.test_quotes_live.py]]
- [[tests.test_replay_determinism.py]]
- [[tests.test_rutas_acceso_decision.py]]
- [[tests.test_security.py]]
- [[tests.test_server_smoke.py]]
- [[tests.test_trading_agent_ledger.py]]
- [[tests.test_voice_agent_split.py]]
- [[tests.test_voice_os_server.py]]
- [[tests.test_voice_tour.py]]

## ¿Está documentada en CLAUDE.md?

Sí — en la lista **Variables de entorno** de [[Doc CLAUDE]].
