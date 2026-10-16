---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-13"
ruta: "docs/ESTADO.md#L506"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-13 — INFRAESTRUCTURA OPERATIVA, PASOS 1-4 (registro inmutable, versión del grafo, vistas rápidas)

> Sesión de trabajo · `docs/ESTADO.md` línea 506 (18 líneas) · [[Índice de sesiones]]

## Resumen

\- Paso 1: `events` append-only con disparador (UPDATE/DELETE/TRUNCATE bloqueados), columnas txid/seq/release_hash (las filas viejas quedan NULL, nada se reescribe), índice parcial de eventos estructurales; brokerage reutiliza `core/ledger_ddl.safe_ddl`. Ningún código de producción modificaba eventos (prueba estática). - Paso 2: `graph_version` al confirmar (+1 por transacción que cambia la estructura; savepoints y rollbacks no la

## Archivos que menciona

- [[core.ledger_ddl.py]]

← más antigua: [[Sesión 2026-10-12 (e) — BLOQUE 0 DE BRECHAS_V2 - CIFRAS Y PUBLICACIÓN SEGURAS]] · más nueva: [[Sesión 2026-10-13 (b) — INFRAESTRUCTURA OPERATIVA, PASOS 5, 6 y 8]] →
