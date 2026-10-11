---
tipo: "documento"
capa: "Documentación"
ruta: "docs/CLAIM_MODEL.md"
lenguaje: "markdown"
lineas: 47
aliases: ["docs/CLAIM_MODEL.md"]
tags: ["capa/documentacion", "tipo/documento"]
---

# docs/CLAIM_MODEL.md

> Documento · capa [[Capa Documentación]] · 47 líneas · `docs/CLAIM_MODEL.md`

## De qué trata

CLAIM MODEL — tres capas que NO se mezclan — | Capa | Dónde | Quién escribe | |---|---|---| | RAW DATA | proveedores (`core/providers`, `core/company_data`) | nadie la modifica | | GRAPH FACTS | `events` / `objects` / `links` (ontología bitemporal) | Acciones auditadas, ingesta, humanos | | DERIVED CLAIMS | `research_claims` / `research_evidence` / `claim_relations` | agentes (Phase 2) |

## Menciona

- [[core.company_data.py]]
- [[research.confidence.py]]
