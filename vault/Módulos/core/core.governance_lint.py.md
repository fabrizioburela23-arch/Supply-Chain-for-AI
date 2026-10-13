---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/governance_lint.py"
lenguaje: "python"
lineas: 270
aliases: ["core/governance_lint.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/governance_lint.py

> Módulo · capa [[Capa Infraestructura]] · 270 líneas · `core/governance_lint.py`

## Para qué sirve

EL lint de los artefactos de gobernanza (docs/INFRA_OPERATIVA.md §5.2; pasos 9 y 25).

## API pública

- `P(code, es, en)` _(línea 39)_
- `diff_kind(old, new)` — 'none' | 'add' (solo claves nuevas) | 'change' (algo quitado o distinto). _(línea 44)_
- `bump_matches(ck, psv, sv)` — ¿El salto de versión parent→sv es del tamaño que declara change_kind? major sube X; minor sube Y con el mismo X; patch sube Z con el mismo … _(línea 58)_
- `needed_kind(old_params, new_params)` — El change_kind MÍNIMO honesto para pasar de old a new: None (nada cambia), 'minor' (solo agrega), 'major'. _(línea 71)_
- `next_semver(versions, parent_semver, change_kind)` — La siguiente versión libre del tamaño declarado sobre `parent_semver`, por encima de TODAS las existentes con el mismo prefijo (repositorio … _(línea 77)_
- `semver_problems(docs)` — [{code, es, en}] de un conjunto {(id, semver): doc} (el del repositorio, o el repositorio + la base + la propuesta). _(línea 89)_
- `tunables()` — governance/tunables.json → {artifact_id: {ruta: {type, min, max, step?, label_es/en, help_es/en}}, _relations}. _(línea 152)_
- `get_path(params, path)` _(línea 165)_
- `set_path(params, path, value)` _(línea 174)_
- `schema_problems(aid, base_params, new_params)` — Lo cambiado entre base y new debe estar en la tabla de afinables, con su tipo y dentro de [min, max]. _(línea 190)_
- `tunables_problems(latest)` — Revisión del propio esquema contra los artefactos del repositorio (la corre --check): cada ruta afinable existe en la versión más alta de … _(línea 230)_
- `mirror_problems(aid, params)` — Espejos de UNA versión (la propuesta de la app): rel_weights = vocabulario; artefactos con espejo fuera. _(línea 258)_

**Internas** (empiezan con `_`): `_flat`

## Depende de

- [[core.governance.py]] — importa `governance`
- [[ontology.vocabulary.py]] — importa `vocabulary`

## Lo usan

- [[core.governance_flow.py]] — lo importa
- [[scripts.build_governance.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_governance.py]]
- [[tests.test_governance_flow.py]]
