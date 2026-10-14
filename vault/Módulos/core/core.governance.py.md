---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/governance.py"
lenguaje: "python"
lineas: 1109
aliases: ["core/governance.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/governance.py

> Módulo · capa [[Capa Infraestructura]] · 1.109 líneas · `core/governance.py`

## Para qué sirve

EL registro de gobernanza (docs/INFRA_OPERATIVA.md §5.1-§5.4; paso 9 del plan).

## API pública

- clase `GovernanceError` _(línea 77)_
- `canonical(obj)` _(línea 82)_
- `hashed_body(doc)` _(línea 87)_
- `artifact_hash(doc)` _(línea 91)_
- `release_hash_of(artifact_hashes)` — sha256 del mapa {artifact_id: hash} canónico (sin el código). _(línea 95)_
- `semver_key(v)` _(línea 100)_
- `artifact_path(aid, semver)` _(línea 108)_
- `read_artifact_file(path)` _(línea 112)_
- `scan_repo()` — {(id, semver): doc} de todos los archivos de governance/artifacts. _(línea 125)_
- `latest_per_id(docs)` _(línea 137)_
- clase `Bundle` — Release resuelto en memoria: {artifact_id: {semver, hash, params}} + sello. _(línea 145)_
- `load_manifest()` _(línea 169)_
- `repo_bundle()` — El release PROPUESTO por el repositorio (manifest.json), verificado contra los archivos. Cacheado. _(línea 174)_
- `repo_plain_artifact(aid)` — La versión del MANIFEST de `aid` (sin selección por entorno) o None. Es lo que lee un artefacto que el release vigente de la base no trae … _(línea 213)_
- `env_name(aid)` _(línea 220)_
- `active()` — El Bundle vigente: el de la base si hay base y se pudo cargar; si no, el del repositorio. _(línea 233)_
- `release()` — (release_hash, etiqueta) — κ de configuración para decisiones, eventos y vistas. _(línea 241)_
- `fallbacks()` — {artifact_id: {semver, hash}} que el release VIGENTE de la base NO trae y que el código lee del archivo del repositorio (sin aprobar; p. … _(línea 267)_
- `param(aid, key, default=…)` _(línea 284)_
- `section(aid)` — Copia de los parámetros del artefacto vigente (para inicializar estructuras del módulo). _(línea 293)_
- `artifact_hash_of(aid)` _(línea 298)_
- `artifact_semver(aid)` _(línea 302)_
- `policy_ref(aid)` — 'policy.broker_risk@1.0.0' + hash — para citar la política en una decisión. _(línea 306)_
- `bind(target, aid, mapping)` — Asigna constantes de un módulo desde el artefacto `aid` y las re-asigna si cambia el release. `target`: dict de globals() o nombre de … _(línea 313)_
- `on_release_change(fn)` — Oyente: fn(old_hash, new_hash) tras un cambio de release (vistas, cachés). _(línea 343)_
- `bootstrap_db(engine=…)` — init_schema: registra en gov_artifacts los artefactos del repo cuyo hash es nuevo (decisión governance.propose) y, si la base no tiene … _(línea 392)_
- `registered()` — {(id, semver): {...}} de gov_artifacts (vacío sin base). _(línea 514)_
- `refresh(engine=…)` — Lee el release vigente de la base (y la selección por entorno), verifica los cuerpos por hash y lo pone en vigor. Barato (2 consultas … _(línea 555)_
- `refresh_job()` — Tarea del reloj (system:governance_refresh). Paso 25: una activación PROGRAMADA entra aquí al llegar su hora (refresh toma el release de … _(línea 655)_
- `ratify(session, principal, release_hash=…, note=…)` — Ratifica (con PIN, una persona) el release vigente o `release_hash` → decisión governance.ratify. No es un UPDATE: el estado ratificado se … _(línea 670)_
- `available_artifact(aid, semver)` — {semver, hash, params, kind, change_kind, changelog_es/en, activation} de una versión DISPONIBLE (archivo del repositorio; con base, además … _(línea 699)_
- clase `counterfactual` — `with counterfactual({'kernel.params': '2.0.0'}):` — ESTE hilo lee esas versiones (archivo del repositorio, verificado por hash) en vez de … _(línea 727)_
- clase `pinned` — `with pinned(arts):` — como `counterfactual`, pero con los cuerpos YA resueltos y verificados por hash ({artifact_id: {semver, hash, … _(línea 745)_
- `proposals()` — Versiones DISPONIBLES (repositorio) distintas de la vigente, por artefacto: lo que el 🩺 ofrece activar con PIN. [{id, semver, … _(línea 754)_
- clase `GovernanceConflict` — Conflicto del flujo (paso 25) con su código para la API: 'scheduled_pending', 'not_cancellable'… _(línea 811)_
- `scheduled_pending(conn_or_session)` — Activaciones PROGRAMADAS que aún no empezaron y no se cancelaron: [{decision_id, release_hash, semver, effective_from, changes, … _(línea 819)_
- `due_unapplied(conn_or_session)` — Activaciones PROGRAMADAS cuya hora ya llegó y que el reloj todavía no aplicó (sin decisión 'applies'). _(línea 841)_
- `activate(session, principal, selection, note=…, effective_from=…, validation_id=…)` — Activa YA (D5: inmediato) el release vigente con las versiones de `selection` ({artifact_id: semver}) sustituidas → fila nueva en … _(línea 847)_
- `env_warnings()` — D2: variables de entorno numéricas que ya no mandan y CONTRADICEN al artefacto vigente. _(línea 1047)_
- `status()` _(línea 1070)_
- `explain(lang=…)` _(línea 1082)_

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
- [[core.impls.py]] — lo importa
- [[core.ledger_guard.py]] — lo importa
- [[core.numbers.py]] — lo importa
- [[core.replay.py]] — lo importa
- [[core.retention.py]] — lo importa
- [[core.risk_report.py]] — lo importa
- [[core.scenario_engine.py]] — lo importa
- [[core.scenario_pnl.py]] — lo importa
- [[core.world.py]] — lo importa
- [[matrix.api.py]] — lo importa
- [[matrix.engine.py]] — lo importa
- [[matrix.tensor.py]] — lo importa
- [[ontology.agents.py]] — lo importa
- [[ontology.checkpoints.py]] — lo importa
- [[ontology.db.py]] — lo importa
- [[ontology.service.py]] — lo importa
- [[ontology.vocabulary.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[research.outcomes.py]] — lo importa
- [[scripts.build_governance.py]] — lo importa
- [[scripts.calibrate_kernel.py]] — lo importa
- [[scripts.migrate_v0_to_ontology.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 24 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV GOV_RELEASE]]

## Pruebas que lo cubren

- [[tests.test_checkpoints.py]]
- [[tests.test_cierre_defectos.py]]
- [[tests.test_gates_ir_fresh.py]]
- [[tests.test_gates_resulting_state.py]]
- [[tests.test_genui_schema.py]]
- [[tests.test_governance.py]]
- [[tests.test_governance_activation.py]]
- [[tests.test_governance_flow.py]]
- [[tests.test_governance_seed_parity.py]]
- [[tests.test_impl_registry.py]]
- [[tests.test_kernel_monotone_edges.py]]
- [[tests.test_kernel_monotone_severity.py]]
- [[tests.test_kernel_reference_figures.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_guard.py]]
- [[tests.test_matrix.py]]
- [[tests.test_ontology_actions.py]]
- [[tests.test_replay_determinism.py]]
- [[tests.test_retention_purge.py]]
- [[tests.test_review_batch_g.py]]
- [[tests.test_review_infra_c.py]]
- [[tests.test_risk_robust.py]]
- [[tests.test_scenario_kernel.py]]
- [[tests.test_scenario_pnl.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (c) — INFRAESTRUCTURA OPERATIVA, PASOS 7, 9, 10 y 13]]
