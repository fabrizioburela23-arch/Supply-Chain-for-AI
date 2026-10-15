---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "scripts/import_companies.py"
lenguaje: "python"
lineas: 311
aliases: ["scripts/import_companies.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# scripts/import_companies.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 311 líneas · `scripts/import_companies.py`

## Para qué sirve

terminal del importador de fichas khipus.company/1 (EXPANSION_5K E2.4).

## API pública

- `main(argv=…)` _(línea 151)_

**Internas** (empiezan con `_`): `_die`, `_http`, `_http_text`, `_upload`, `_gz_text`, `_lote2`

## Depende de

- [[ontology.company_import.py]] — importa `company_import`
- [[ontology.db.py]] — importa `init_schema`, `session_scope`

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

_Además lo importan 2 pruebas (lista abajo)._

## Endpoints que llama

- `GET /api/ontology/import/runs` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/import/apply` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/import/files` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/import/plan` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/import/rollback` → [[ontology.api.py]] ([[API ontology]])

## Variables de entorno que lee (solo nombres)

- [[ENV DATABASE_URL]]
- [[ENV TRADE_PIN]]

## Pruebas que lo cubren

- [[tests.test_import_lote2.py]]
- [[tests.test_import_lote2_e2e.py]]
- [[tests.test_lotek_fixer.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-14 (c) — LOTE K - IMPORTADOR DE EMPRESAS, PAÍSES ISO-2, CATEGORÍAS, CHAT]]
