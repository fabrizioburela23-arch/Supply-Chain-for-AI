---
tipo: "modulo"
capa: "Datos del catálogo"
ruta: "scripts/build_categories.py"
lenguaje: "python"
lineas: 365
aliases: ["scripts/build_categories.py"]
tags: ["capa/datos-catalogo", "tipo/modulo"]
---

# scripts/build_categories.py

> Módulo · capa [[Capa Datos del catálogo]] · 365 líneas · `scripts/build_categories.py`

## Para qué sirve

genera nodes/categories_extra.js desde data/categories.json (FUENTE ÚNICA).

## API pública

- `load(path=…)` _(línea 38)_
- `validate(doc)` — Lista de problemas (vacía = JSON válido). Reglas: ids únicos y con forma; es/en/sector/cssVar en todas; sector conocido; cssVar = --c-&lt;id>; … _(línea 43)_
- `aliases(doc)` — alias → id consolidado (incluye el id mismo → id). _(línea 94)_
- `resolve(cat, doc=…)` — Categoría consolidada de un id o alias (None si no existe). _(línea 104)_
- `render(doc)` _(línea 113)_
- `css_lines(doc, theme)` — Variables CSS de las categorías NUEVAS con color propio, agrupadas por sector (para pegar en app.html). _(línea 145)_
- `delta_e(h1, h2)` — ΔE CIE76 entre dos hex (≈ 2,3 = apenas perceptible; < 5 = iguales en una leyenda; ≥ 10 = distintos). _(línea 199)_
- `app_css_colors(theme, app_path=…)` — {id: hex} de TODAS las variables --c-\* del tema en app.html (:root = claro, .dark = oscuro). _(línea 217)_
- `recolor(doc, min_de=…, app_path=…)` — Reasigna el color de cada categoría NUEVA (color_source css, origin ≠ catalog) para que quede a ≥ `min_de` (ΔE CIE76) de todos los colores … _(línea 226)_
- `min_delta_e(doc, theme, app_path=…)` — ΔE mínimo entre cada categoría nueva y TODAS las demás variables --c-\* del tema (lo que vigila el test). _(línea 276)_
- `counts(doc, snapshot=…)` — Empresas por categoría en el snapshot (las nuevas tienen 0 hoy). _(línea 294)_
- `main(argv=…)` _(línea 310)_

**Internas** (empiezan con `_`): `_js_obj`, `_hex_rgb`, `_rgb_hex`, `_lab`, `_hsl`, `_hex_hsl`

## Depende de

- [[app.html]] — lo nombra por su ruta
- [[data.categories.json]] — lo nombra por su ruta
- [[data.grafo_v0.json]] — lo nombra por su ruta
- [[nodes.categories_extra.js]] — lo nombra por su ruta

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_catalog_fix_categories.py]]
