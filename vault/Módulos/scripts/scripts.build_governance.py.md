---
tipo: "modulo"
capa: "Infraestructura"
ruta: "scripts/build_governance.py"
lenguaje: "python"
lineas: 226
aliases: ["scripts/build_governance.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# scripts/build_governance.py

> Módulo · capa [[Capa Infraestructura]] · 226 líneas · `scripts/build_governance.py`

## Para qué sirve

mantiene governance/manifest.json (docs/INFRA_OPERATIVA.md §5.1-§5.3; paso 9).

## API pública

- `expected_generated(aid)` — Parámetros que DEBE tener un artefacto generado según su fuente de hoy (o None si no aplica). _(línea 54)_
- `mirror_problems(latest)` _(línea 71)_
- `semver_problems(docs)` — Textos (es) de los problemas semver — core.governance_lint.semver_problems los da bilingües. _(línea 96)_
- `releasable(docs)` — Las versiones que pueden entrar en el release PROPUESTO del repositorio: todas menos las marcadas `"activation": "pin"` (un MAJOR que solo … _(línea 101)_
- `build_manifest(docs, release_semver)` _(línea 108)_
- `check(verbose=…)` _(línea 129)_
- `bump(spec, changelog_es, changelog_en)` — \--bump id=semver:kind → archivo nuevo de un artefacto GENERADO con los parámetros de su fuente de hoy. _(línea 165)_
- `write(release_semver=…)` _(línea 189)_
- `main(argv=…)` _(línea 209)_

**Internas** (empiezan con `_`): `_vocab_sha`, `_ir`, `_dump`

## Depende de

- [[core.decisions.py]] — importa `decisions`
- [[core.governance.py]] — importa `governance`
- [[core.governance_lint.py]] — importa `governance_lint`
- [[ontology.vocabulary.py]] — importa `vocabulary`
- [[ontology.vocabulary.json]] — lo nombra por su ruta

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

_Además lo importan 4 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_genui_schema.py]]
- [[tests.test_governance.py]]
- [[tests.test_governance_flow.py]]
- [[tests.test_import_governance.py]]
- [[tests.test_review_infra_c.py]]
