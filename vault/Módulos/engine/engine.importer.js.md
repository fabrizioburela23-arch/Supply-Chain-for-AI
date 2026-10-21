---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/importer.js"
lenguaje: "javascript"
lineas: 998
aliases: ["engine/importer.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/importer.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 998 líneas · `engine/importer.js`

## Para qué sirve

EXPANSION_5K E2.7 · 🩺 Sistema → Diagnóstico → «📥 Importar empresas». Panel de la tubería de importación (ontology/company_import.py, rutas /api/ontology/import/\*): · lista los PAQUETES del repositorio (GET /import/packages: «Lote 2 — 386 empresas completas»); · «Ver plan» SIN PIN (GET /import/packages/plan: lectura pura) en palabras simples: se crean / se fusionan / vínculos vivos · propuestos · pendientes / categorías / ¿qué cambia? (ρ y TSMC antes → después) / avisos; · «Aplicar» = confirmación + copia de seguridad + nombre EXACTO de la base + PIN (window._tradeFetch) y manda expect.plan_sha (la huella del plan que la persona vio); el servidor recalcula y, si cambió → …

## API pública (globales que define)

`window.KhipuImporter`

## Depende de

- [[app.html]] — usa `_tradeFetch`
- [[engine.app_main.js]] — usa `BASE`, `LANG`
- [[engine.explain.js]] — usa `explainMetric`, `explainRegister`
- [[engine.toast.js]] — usa `KhipuToast`, `khipuActor`

## Lo usan

- [[engine.app_main.js]] — usa `KhipuImporter`
- [[engine.app_main.js]] — lo nombra por su ruta

## Endpoints que llama

- `GET /api/ontology/actions` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/import/packages/plan` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/import/packages` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/import/runs` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/links/review` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/actions/<action_type>` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/import/apply` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/import/files` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/import/plan` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/import/rollback` → [[ontology.api.py]] ([[API ontology]])

## Pruebas que lo cubren

- [[tests.test_import_panel_browser.py]]
- [[tests.test_import_panel_static.py]]
- [[tests.test_link_review.py]]
- [[tests.test_lotel_fixer.py]]
