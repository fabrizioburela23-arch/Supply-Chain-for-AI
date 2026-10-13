---
tipo: "modulo"
capa: "Infraestructura"
ruta: "scripts/build_governance.py"
lenguaje: "python"
lineas: 275
aliases: ["scripts/build_governance.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# scripts/build_governance.py

> Módulo · capa [[Capa Infraestructura]] · 275 líneas · `scripts/build_governance.py`

## Para qué sirve

mantiene governance/manifest.json (docs/INFRA_OPERATIVA.md §5.1-§5.3; paso 9).

## API pública

- `expected_generated(aid)` — Parámetros que DEBE tener un artefacto generado según su fuente de hoy (o None si no aplica). _(línea 52)_
- `mirror_problems(latest)` _(línea 69)_
- `semver_problems(docs)` _(línea 116)_
- `build_manifest(docs, release_semver)` _(línea 160)_
- `check(verbose=…)` _(línea 179)_
- `bump(spec, changelog_es, changelog_en)` — \--bump id=semver:kind → archivo nuevo de un artefacto GENERADO con los parámetros de su fuente de hoy. _(línea 214)_
- `write(release_semver=…)` _(línea 238)_
- `main(argv=…)` _(línea 258)_

**Internas** (empiezan con `_`): `_vocab_sha`, `_ir`, `_diff_kind`, `_bump_matches`, `_dump`

## Depende de

- [[core.decisions.py]] — importa `decisions`
- [[core.governance.py]] — importa `governance`
- [[ontology.vocabulary.py]] — importa `vocabulary`
- [[ontology.vocabulary.json]] — lo nombra por su ruta

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_governance.py]]
- [[tests.test_review_infra_c.py]]
