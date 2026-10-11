---
tipo: "datos"
capa: "Ontología y grafo temporal"
ruta: "ontology/vocabulary.json"
lenguaje: "json"
lineas: 256
aliases: ["ontology/vocabulary.json"]
tags: ["capa/ontologia", "tipo/datos"]
---

# ontology/vocabulary.json

> Datos · capa [[Capa Ontología y grafo temporal]] · 256 líneas · `ontology/vocabulary.json`

## Para qué sirve

REGISTRO ÚNICO del vocabulario del grafo. Añadir un tipo de objeto, un tipo de relación o un sector se hace AQUÍ (dato), no editando código en 29 sitios. El servidor lo sirve en GET /api/vocabulary para que el cliente deje de mantener copias. Regla de oro: lo que no está aquí NO se clasifica en silencio — se reporta como desconocido (ver /api/vocabulary/unknown).

## Qué datos contiene

| Clave | Tipo | Tamaño / valor |
|---|---|---|
| `version` | número | 1 |
| `object_types` | objeto | 18 |
| `relation_types` | objeto | 15 |
| `source_kinds` | objeto | 7 |

## Depende de

_Nada interno._

## Lo usan

- [[ontology.vocabulary.py]] — lo nombra por su ruta
- [[scripts.audit_graph.py]] — lo nombra por su ruta

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (gg) — DIRECCIONES AL REVÉS + PESO DE LICENCIAS + PISO DEL KERNEL]]
- [[Sesión 2026-10-06 (ff) — ONTOLOGÍA NIVEL 2 - TENSORES + AUTO-CONEXIÓN (sw v241)]]
- [[Sesión 2026-10-04 (h) — MISIÓN DE REPARACIÓN P0 INVESTIGACIÓN (R1-R6, sw v201)]]
- [[Sesión 2026-09-22 al 24 — PHASE 1 Live Investment Graph COMPLETA + velocidad + 3D temporal]]
- [[Sesión 2026-08-02 — Expansión multicapa COMPLETA (olas 1-6) - 949 nodos, 13 sectores, 70]]
