---
tipo: "modulo"
capa: "Datos del catálogo"
ruta: "scripts/ingest_multicapa.py"
lenguaje: "python"
lineas: 343
aliases: ["scripts/ingest_multicapa.py"]
tags: ["capa/datos-catalogo", "tipo/modulo"]
---

# scripts/ingest_multicapa.py

> Módulo · capa [[Capa Datos del catálogo]] · 343 líneas · `scripts/ingest_multicapa.py`

## Para qué sirve

Ingesta de la EXPANSIÓN MULTICAPA de Fabrizio.

## API pública

- `parse_blocks(text)` — Divide el doc en bloques ### y clasifica nodo/FACTOR/ASIENTO. _(línea 54)_
- `parse_node(head, body)` _(línea 83)_
- `parse_factor(head, body)` _(línea 169)_
- `parse_seat(head, body)` _(línea 185)_
- `main()` _(línea 193)_

**Internas** (empiezan con `_`): `_fields`

## Depende de

- [[data.grafo_v0.json]] — lo nombra por su ruta
- [[data.multicapa_factors_seats.json]] — lo nombra por su ruta
- [[nodes.nodes_multicapa.js]] — lo nombra por su ruta

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-08-02 — Expansión multicapa COMPLETA (olas 1-6) - 949 nodos, 13 sectores, 70]]
