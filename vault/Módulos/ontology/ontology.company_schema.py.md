---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/company_schema.py"
lenguaje: "python"
lineas: 743
aliases: ["ontology/company_schema.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/company_schema.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 743 líneas · `ontology/company_schema.py`

## Para qué sirve

espejo Pydantic v2 de `data/import/company.schema.json` (khipus.company/1; E2.1).

## API pública

- clase `Evidence` _(línea 73)_
- clase `RelationEvidence` — La evidencia de un vínculo exige tipo de fuente y cita textual. _(línea 83)_
- clase `FactBase` _(línea 89)_
- clase `FStr` _(línea 102)_
- clase `FTextEs` _(línea 106)_
- clase `FNum` _(línea 111)_
- clase `FInt` _(línea 116)_
- clase `FPct` _(línea 120)_
- clase `FDate` _(línea 124)_
- clase `FBool` _(línea 128)_
- clase `FMoney` _(línea 132)_
- clase `FCountry` _(línea 138)_
- clase `FSharePct` _(línea 142)_
- clase `FQty` _(línea 146)_
- clase `FStatus` _(línea 151)_
- clase `NationalRegistry` _(línea 157)_
- clase `CounterpartyIds` _(línea 163)_
- clase `Counterparty` _(línea 176)_
- clase `OtherName` _(línea 185)_
- clase `GeoPoint` _(línea 192)_
- clase `Identity` _(línea 200)_
- clase `ResearchMeta` _(línea 216)_
- clase `Listing` _(línea 231)_
- clase `CatProposed` _(línea 250)_
- clase `Classification` _(línea 263)_
- clase `KeyPerson` _(línea 281)_
- clase `Profile` _(línea 289)_
- clase `Holding` _(línea 303)_
- clase `Corporate` _(línea 311)_
- clase `MarketPosition` _(línea 320)_
- clase `Product` _(línea 342)_
- clase `Capacity` _(línea 354)_
- clase `Facility` _(línea 359)_
- clase `Segment` _(línea 380)_
- clase `AnnualFinancials` _(línea 385)_
- clase `QuarterlyFinancials` _(línea 397)_
- clase `Financials` _(línea 409)_
- clase `FundingRound` _(línea 418)_
- clase `RevenueByRegion` _(línea 434)_
- clase `Subsidy` _(línea 439)_
- clase `Exposure` _(línea 449)_
- clase `RestrictedList` _(línea 458)_
- clase `Litigation` _(línea 471)_
- clase `Regulatory` _(línea 481)_
- clase `Risk` _(línea 486)_
- clase `Innovation` _(línea 496)_
- clase `Esg` _(línea 502)_
- clase `TimelineEvent` _(línea 511)_
- clase `FacilityRef` _(línea 526)_
- clase `Dependency` _(línea 544)_
- clase `Relation` _(línea 561)_
- clase `LiveHooks` _(línea 587)_
- clase `CompanyRecord` — UNA empresa = una ficha khipus.company/1 (una línea de un .jsonl). _(línea 596)_
- `validate_record(data)` — Dict (o texto JSON) → (CompanyRecord | None, errores). Modo JSON estricto: lo que no entra en el artefacto no entra aquí. Cada error: … _(línea 649)_
- `json_schema()` — El JSON Schema que Pydantic genera para la ficha (la prueba lo compara con el artefacto). _(línea 671)_
- `canonical_shape(schema)` — Expande \$ref/allOf, quita títulos/descripciones/defaults/condicionales (if-then-anyOf de obligatorios, que aquí son validadores) y deja … _(línea 681)_
- `load_artifact_schema(path=…)` — El JSON Schema del repositorio (data/import/company.schema.json). _(línea 738)_

**Internas** (empiezan con `_`): `_M`, `_path`

## Depende de

_Nada interno._

## Lo usan

- [[ontology.company_import.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_import_schema.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-14 (c) — LOTE K - IMPORTADOR DE EMPRESAS, PAÍSES ISO-2, CATEGORÍAS, CHAT]]
