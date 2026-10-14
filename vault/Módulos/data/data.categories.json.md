---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "data/categories.json"
lenguaje: "json"
lineas: 2787
aliases: ["data/categories.json"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# data/categories.json

> Datos · capa [[Capa Datos del catálogo]] · 2.787 líneas · `data/categories.json`

## Para qué sirve

FUENTE ÚNICA de las categorías del catálogo (108 de nodes/\*.js + 55 del lote 2026-10-14, aprobadas por defecto: Fabrizio puede rechazar poniendo status "rejected"). nodes/categories_extra.js se GENERA con python scripts/build_categories.py (nunca editarlo a mano); las variables CSS --c-&lt;id> de las categorías con color_source "css" viven en app.html (claro en :root, oscuro en .dark) y deben coincidir con `color`; color_source "sector" = nodes_multicapa.js las pinta en vivo con el color de su sector. `aliases` = ids que un lote importado puede traer y que se consolidan en esta categoría (battery_components → battery_cells). `x` = posición en el eje semántico del mapa (0 aguas arriba → 1 aguas …

## Qué datos contiene

| Clave | Tipo | Tamaño / valor |
|---|---|---|
| `as_of` | fecha | `2026-10-14` |
| `merged` | objeto | 1 |
| `sectors` | objeto | 13 |
| `categories` | objeto | 163 |

## Depende de

_Nada interno._

## Lo usan

- [[ontology.vocabulary.py]] — lo nombra por su ruta
- [[scripts.build_categories.py]] — lo nombra por su ruta

## Pruebas que lo cubren

- [[tests.test_catalog_fix_categories.py]]
- [[tests.test_governance.py]]
- [[tests.test_import_adapter.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-14 (c) — LOTE K - IMPORTADOR DE EMPRESAS, PAÍSES ISO-2, CATEGORÍAS, CHAT]]
