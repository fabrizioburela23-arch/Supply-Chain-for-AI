---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/governance.py"
lenguaje: "python"
lineas: 1089
aliases: ["core/governance.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/governance.py

> Módulo · capa [[Capa Infraestructura]] · 1.089 líneas · `core/governance.py`

## Para qué sirve

EL registro de gobernanza (docs/INFRA_OPERATIVA.md §5.1-§5.4; paso 9 del plan).

## API pública

- clase `GovernanceError` _(línea 66)_
- `canonical(obj)` _(línea 71)_
- `hashed_body(doc)` _(línea 76)_
- `artifact_hash(doc)` _(línea 80)_
- `release_hash_of(artifact_hashes)` — sha256 del mapa {artifact_id: hash} canónico (sin el código). _(línea 84)_
- `semver_key(v)` _(línea 89)_
- `artifact_path(aid, semver)` _(línea 97)_
- `read_artifact_file(path)` _(línea 101)_
- `scan_repo()` — {(id, semver): doc} de todos los archivos de governance/artifacts. _(línea 114)_
- `latest_per_id(docs)` _(línea 126)_
- clase `Bundle` — Release resuelto en memoria: {artifact_id: {semver, hash, params}} + sello. _(línea 134)_
- `load_manifest()` _(línea 158)_
- `repo_bundle()` — El release PROPUESTO por el repositorio (manifest.json), verificado contra los archivos. Cacheado. _(línea 163)_
- `repo_plain_artifact(aid)` — La versión del MANIFEST de `aid` (sin selección por entorno) o None. Es lo que lee un artefacto que el release vigente de la base no trae … _(línea 202)_
- `env_name(aid)` _(línea 209)_
- `active()` — El Bundle vigente: el de la base si hay base y se pudo cargar; si no, el del repositorio. _(línea 222)_
- `release()` — (release_hash, etiqueta) — κ de configuración para decisiones, eventos y vistas. _(línea 230)_
- `fallbacks()` — {artifact_id: {semver, hash}} que el release VIGENTE de la base NO trae y que el código lee del archivo del repositorio (sin aprobar; p. … _(línea 256)_
- `param(aid, key, default=…)` _(línea 273)_
- `section(aid)` — Copia de los parámetros del artefacto vigente (para inicializar estructuras del módulo). _(línea 282)_
- `artifact_hash_of(aid)` _(línea 287)_
- `artifact_semver(aid)` _(línea 291)_
- `policy_ref(aid)` — 'policy.broker_risk@1.0.0' + hash — para citar la política en una decisión. _(línea 295)_
- `bind(target, aid, mapping)` — Asigna constantes de un módulo desde el artefacto `aid` y las re-asigna si cambia el release. `target`: dict de globals() o nombre de … _(línea 302)_
- `on_release_change(fn)` — Oyente: fn(old_hash, new_hash) tras un cambio de release (vistas, cachés). _(línea 332)_
- `bootstrap_db(engine=…)` — init_schema: registra en gov_artifacts los artefactos del repo cuyo hash es nuevo (decisión governance.propose) y, si la base no tiene … _(línea 381)_
- `registered()` — {(id, semver): {...}} de gov_artifacts (vacío sin base). _(línea 503)_
- `refresh(engine=…)` — Lee el release vigente de la base (y la selección por entorno), verifica los cuerpos por hash y lo pone en vigor. Barato (2 consultas … _(línea 544)_
- `refresh_job()` — Tarea del reloj (system:governance_refresh). Paso 25: una activación PROGRAMADA entra aquí al llegar su hora (refresh toma el release de … _(línea 644)_
- `ratify(session, principal, release_hash=…, note=…)` — Ratifica (con PIN, una persona) el release vigente o `release_hash` → decisión governance.ratify. No es un UPDATE: el estado ratificado se … _(línea 659)_
- `available_artifact(aid, semver)` — {semver, hash, params, kind, change_kind, changelog_es/en, activation} de una versión DISPONIBLE (archivo del repositorio; con base, además … _(línea 688)_
- clase `counterfactual` — `with counterfactual({'kernel.params': '2.0.0'}):` — ESTE hilo lee esas versiones (archivo del repositorio, verificado por hash) en vez de … _(línea 716)_
- `proposals()` — Versiones DISPONIBLES (repositorio) distintas de la vigente, por artefacto: lo que el 🩺 ofrece activar con PIN. [{id, semver, … _(línea 734)_
- clase `GovernanceConflict` — Conflicto del flujo (paso 25) con su código para la API: 'scheduled_pending', 'not_cancellable'… _(línea 791)_
- `scheduled_pending(conn_or_session)` — Activaciones PROGRAMADAS que aún no empezaron y no se cancelaron: [{decision_id, release_hash, semver, effective_from, changes, … _(línea 799)_
- `due_unapplied(conn_or_session)` — Activaciones PROGRAMADAS cuya hora ya llegó y que el reloj todavía no aplicó (sin decisión 'applies'). _(línea 821)_
- `activate(session, principal, selection, note=…, effective_from=…, validation_id=…)` — Activa YA (D5: inmediato) el release vigente con las versiones de `selection` ({artifact_id: semver}) sustituidas → fila nueva en … _(línea 827)_
- `env_warnings()` — D2: variables de entorno numéricas que ya no mandan y CONTRADICEN al artefacto vigente. _(línea 1027)_
- `status()` _(línea 1050)_
- `explain(lang=…)` _(línea 1062)_

**Internas** (empiezan con `_`): `_bundle`, `_db_on`, `_art`, `_apply_one`, `_apply_bindings`, `_swap`, `_engine`, `_tables_ready`, `_bootstrap_write`, `_parent_hash`, `_load_registered`, `_registered_doc`, `_ratified_releases`, `_bump_release_semver`, `_regression_for`, `_semver_major_changed`, `_reset_for_tests`

## Depende de

- [[core.decisions.py]] — importa `canonical`, `decisions`
- [[core.governance_flow.py]] — importa `governance_flow`
- [[core.governance_shadow.py]] — importa `governance_shadow`
- [[core.identity.py]] — importa `identity`
- [[ontology.db.py]] — importa `_get_engine`, `ontology.db`, `session_scope`

## Lo usan

- [[brokerage.risk.py]] — lo importa
- [[brokerage.service.py]] — lo importa
- [[core.decide.py]] — lo importa
- [[core.decision_sites.py]] — lo importa
- [[core.decisions.py]] — lo importa
- [[core.governance_api.py]] — lo importa
- [[core.governance_flow.py]] — lo importa
- [[core.governance_lint.py]] — lo importa
- [[core.governance_preview.py]] — lo importa
- [[core.governance_shadow.py]] — lo importa
- [[core.ledger_guard.py]] — lo importa
- [[core.numbers.py]] — lo importa
- [[core.retention.py]] — lo importa
- [[core.scenario_engine.py]] — lo importa
- [[core.world.py]] — lo importa
- [[matrix.engine.py]] — lo importa
- [[matrix.tensor.py]] — lo importa
- [[ontology.agents.py]] — lo importa
- [[ontology.checkpoints.py]] — lo importa
- [[ontology.db.py]] — lo importa
- [[ontology.service.py]] — lo importa
- [[ontology.vocabulary.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[scripts.build_governance.py]] — lo importa
- [[scripts.migrate_v0_to_ontology.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 17 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV GOV_RELEASE]]

## Pruebas que lo cubren

- [[tests.test_checkpoints.py]]
- [[tests.test_gates_ir_fresh.py]]
- [[tests.test_gates_resulting_state.py]]
- [[tests.test_governance.py]]
- [[tests.test_governance_activation.py]]
- [[tests.test_governance_flow.py]]
- [[tests.test_governance_seed_parity.py]]
- [[tests.test_kernel_monotone_severity.py]]
- [[tests.test_kernel_reference_figures.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_guard.py]]
- [[tests.test_matrix.py]]
- [[tests.test_ontology_actions.py]]
- [[tests.test_retention_purge.py]]
- [[tests.test_review_batch_g.py]]
- [[tests.test_review_infra_c.py]]
- [[tests.test_scenario_kernel.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (c) — INFRAESTRUCTURA OPERATIVA, PASOS 7, 9, 10 y 13]]
