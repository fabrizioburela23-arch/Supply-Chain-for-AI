---
tipo: "modulo"
capa: "Datos del catálogo"
ruta: "scripts/ingest_enrichment_md.py"
lenguaje: "python"
lineas: 404
aliases: ["scripts/ingest_enrichment_md.py"]
tags: ["capa/datos-catalogo", "tipo/modulo"]
---

# scripts/ingest_enrichment_md.py

> Módulo · capa [[Capa Datos del catálogo]] · 404 líneas · `scripts/ingest_enrichment_md.py`

## Para qué sirve

Ingesta de informes de enriquecimiento.

## API pública

- `norm_target(t)` _(línea 82)_
- clase `Resolver` _(línea 96)_
- `parse_blocks(md)` — Devuelve lista de (section, header, lines) para cada bloque ###. _(línea 141)_
- `parse_fields(lines)` _(línea 171)_
- `to_int(v)` _(línea 193)_
- `to_margin(v)` _(línea 201)_
- `mk_mkt(ticker)` _(línea 207)_
- `infer_direction(section, node_id, target_id, ltype, rel, node_sector)` — Devuelve (source, target, motivo). Canónico: source PROVEE a target. _(línea 215)_
- `main()` _(línea 242)_

## Depende de

_Nada interno._

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-07-10 — modo máximo (feedback - perfeccionar Khipu, 555 empresas, vivo, 3D)]]
