---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "data/graph_audit_baseline.json"
lenguaje: "json"
lineas: 21
aliases: ["data/graph_audit_baseline.json"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# data/graph_audit_baseline.json

> Datos · capa [[Capa Datos del catálogo]] · 21 líneas · `data/graph_audit_baseline.json`

## Para qué sirve

Línea base de scripts/audit_graph.py (G1). Las categorías de `metrics` NO pueden empeorar (tests/test_graph_audit.py); `info` es solo informativo. Regenerar con `python scripts/audit_graph.py --write-baseline` tras una mejora consciente.

## Qué datos contiene

| Clave | Tipo | Tamaño / valor |
|---|---|---|
| `generated_at` | fecha | `2026-10-06T04:19:28+00:00` |
| `snapshot_exported_at` | fecha | `2026-10-06T04:19:20.593Z` |
| `nodes` | número | 937 |
| `links` | número | 2510 |
| `metrics` | objeto | 7 |
| `info` | objeto | 3 |

## Depende de

_Nada interno._

## Lo usan

- [[scripts.audit_graph.py]] — lo nombra por su ruta

## Pruebas que lo cubren

- [[tests.test_graph_audit.py]]
