---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/company_schema.py"
lenguaje: "python"
lineas: 780
aliases: ["ontology/company_schema.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/company_schema.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 780 líneas · `ontology/company_schema.py`

## Para qué sirve

espejo Pydantic v2 de `data/import/company.schema.json` (khipus.company/1; E2.1).

## API pública

- clase `Evidence` _(línea 85)_
- clase `RelationEvidence` — La evidencia de un vínculo exige tipo de fuente y cita textual. _(línea 95)_
- clase `FactBase` _(línea 101)_
- clase `FactBaseSoft` — Igual que FactBase pero con `confidence` opcional (ESG y línea de tiempo: el importador pone la de la política … _(línea 114)_
- clase `FStr` _(línea 120)_
- clase `FStrBi` — Texto con su traducción OPCIONAL (regla bilingüe: sanciones y controles de exportación). _(línea 124)_
- clase `FTextEs` _(línea 130)_
- clase `FNum` _(línea 135)_
- clase `FNumSoft` _(línea 140)_
- clase `FInt` _(línea 145)_
- clase `FPct` _(línea 149)_
- clase `FDate` _(línea 153)_
- clase `FBool` _(línea 157)_
- clase `FMoney` _(línea 161)_
- clase `FCountry` _(línea 167)_
- clase `FSharePct` _(línea 171)_
- clase `FSharePctSoft` _(línea 175)_
- clase `FQty` _(línea 179)_
- clase `FStatus` _(línea 184)_
- clase `NationalRegistry` _(línea 190)_
- clase `CounterpartyIds` _(línea 196)_
- clase `Counterparty` _(línea 209)_
- clase `OtherName` _(línea 219)_
- clase `GeoPoint` _(línea 226)_
- clase `Identity` _(línea 234)_
- clase `ResearchMeta` _(línea 250)_
- clase `Listing` _(línea 265)_
- clase `CatProposed` _(línea 284)_
- clase `Classification` _(línea 297)_
- clase `KeyPerson` _(línea 315)_
- clase `Profile` _(línea 323)_
- clase `Holding` _(línea 337)_
- clase `Corporate` _(línea 345)_
- clase `MarketPosition` _(línea 354)_
- clase `Product` _(línea 376)_
- clase `Capacity` _(línea 388)_
- clase `Facility` _(línea 393)_
- clase `Segment` _(línea 414)_
- clase `AnnualFinancials` _(línea 419)_
- clase `QuarterlyFinancials` _(línea 431)_
- clase `Financials` _(línea 443)_
- clase `FundingRound` _(línea 452)_
- clase `RevenueByRegion` _(línea 468)_
- clase `Subsidy` _(línea 473)_
- clase `Exposure` _(línea 483)_
- clase `RestrictedList` _(línea 492)_
- clase `Litigation` _(línea 505)_
- clase `Regulatory` _(línea 515)_
- clase `Risk` _(línea 520)_
- clase `Innovation` _(línea 530)_
- clase `Esg` _(línea 536)_
- clase `TimelineEvent` _(línea 545)_
- clase `FacilityRef` _(línea 560)_
- clase `Dependency` _(línea 578)_
- clase `Relation` _(línea 595)_
- clase `LiveHooks` _(línea 624)_
- clase `CompanyRecord` — UNA empresa = una ficha khipus.company/1 (una línea de un .jsonl). _(línea 633)_
- `validate_record(data)` — Dict (o texto JSON) → (CompanyRecord | None, errores). Modo JSON estricto: lo que no entra en el artefacto no entra aquí. Cada error: … _(línea 686)_
- `json_schema()` — El JSON Schema que Pydantic genera para la ficha (la prueba lo compara con el artefacto). _(línea 708)_
- `canonical_shape(schema)` — Expande \$ref/allOf, quita títulos/descripciones/defaults/condicionales (if-then-anyOf de obligatorios, que aquí son validadores) y deja … _(línea 718)_
- `load_artifact_schema(path=…)` — El JSON Schema del repositorio (data/import/company.schema.json). _(línea 775)_

**Internas** (empiezan con `_`): `_M`, `_path`

## Depende de

_Nada interno._

## Lo usan

- [[core.import_normalize.py]] — lo importa
- [[ontology.company_import.py]] — lo importa

_Además lo importan 3 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_import_sanitize.py]]
- [[tests.test_import_sanitize_schema.py]]
- [[tests.test_import_schema.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-14 (c) — LOTE K - IMPORTADOR DE EMPRESAS, PAÍSES ISO-2, CATEGORÍAS, CHAT]]
