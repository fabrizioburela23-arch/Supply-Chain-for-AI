---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "data/multicapa_factors_seats.json"
lenguaje: "json"
lineas: 1399
aliases: ["data/multicapa_factors_seats.json"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# data/multicapa_factors_seats.json

> Datos · capa [[Capa Datos del catálogo]] · 1.399 líneas · `data/multicapa_factors_seats.json`

## Para qué sirve

Archivo de datos JSON.

## Qué datos contiene

| Clave | Tipo | Tamaño / valor |
|---|---|---|
| `factors` | lista | 69 |
| `seats` | lista | 28 |

## Depende de

_Nada interno._

## Lo usan

- [[scripts.ingest_multicapa.py]] — lo nombra por su ruta
- [[scripts.migrate_v0_to_ontology.py]] — lo nombra por su ruta

## Pruebas que lo cubren

- [[tests.test_matrix.py]]
- [[tests.test_ontology.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-22 al 24 — PHASE 1 Live Investment Graph COMPLETA + velocidad + 3D temporal]]
