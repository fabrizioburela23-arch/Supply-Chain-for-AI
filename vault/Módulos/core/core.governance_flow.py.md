---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/governance_flow.py"
lenguaje: "python"
lineas: 1016
aliases: ["core/governance_flow.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/governance_flow.py

> Módulo · capa [[Capa Infraestructura]] · 1.016 líneas · `core/governance_flow.py`

## Para qué sirve

FLUJO DE GOBERNANZA COMPLETO (docs/INFRA_OPERATIVA.md §5.3; paso 25 del plan).

## API pública

- clase `ProposalRefused` — La propuesta no pasa el lint: `problems` = [{code, es, en}]. _(línea 45)_
- `param_artifacts()` — Artefactos que se pueden proponer desde la app (los que tienen afinables en governance/tunables.json). _(línea 63)_
- `build_proposal(aid, changes, change_kind=…, semver=…, base_semver=…, changelog_es=…, changelog_en=…)` — (doc, diffs, problems) — SIN base: arma la versión nueva y corre el lint. `changes` = {ruta: número}. _(línea 94)_
- `propose(session, principal, aid, changes, change_kind=…, semver=…, base_semver=…, changelog_es=…, changelog_en=…, note=…)` — Registra la propuesta (gov_artifacts + decisión governance.propose 'proposed' de op:…, MISMA transacción). PermissionError sin persona con … _(línea 167)_
- `for_me(sel, before=…, after=…, focus=…)` — «¿Qué cambia para mí?»: por cada empresa de las posiciones del usuario (o de las 10 más críticas) el golpe máximo que puede recibir y a … _(línea 522)_
- `regress(selection, focus=…)` — El reporte de regresión contrafactual (gov-regression/1). Nunca escribe; nunca toca el release vigente. _(línea 631)_
- `validate(principal, aid, semver, focus=…)` — Corre la regresión y la REGISTRA (decisión governance.validate; blob 'validation'). Devuelve {decision_id, report}. Sin base: solo el … _(línea 694)_
- `validate_async(principal, aid, semver, focus=…)` — Lanza la validación en un hilo (una a la vez por versión). Devuelve el estado del trabajo. _(línea 716)_
- `validation(aid, semver)` — Último resultado: el trabajo en memoria si existe; si no, la última decisión governance.validate. _(línea 745)_
- `latest_validation_id(session, selection)` — La decisión governance.validate más reciente de la versión (selección de UN artefacto) o None. _(línea 776)_
- `next_ny_close(now=…)` — D5: los cambios de policy.broker_risk entran por defecto DESPUÉS del cierre de Nueva York (16:05 ET del próximo día hábil; sin feriados). _(línea 789)_
- `parse_effective_from(raw, selection)` — 'now' | None → None (inmediato; salvo policy.broker_risk → cierre de NY, D5) | 'ny_close' | ISO 8601. ValueError si el texto no es una … _(línea 803)_
- `cancel_scheduled(session, principal, decision_id)` — Cancela una activación PROGRAMADA que aún no empezó: decisión governance.activate 'rejected' con subject.cancels (la fila de gov_releases … _(línea 821)_
- `apply_due()` — Reloj (tras refresh): por cada activación programada cuya hora llegó (no cancelada) deja UNA decisión governance.activate 'executed' de … _(línea 846)_
- `record_applied(s, due)` — Una decisión governance.activate 'executed' de system:governance_scheduler (subject.applies) por cada programada de `due` (filas de … _(línea 872)_
- `attribution(session, decision_id)` — Qué release y qué versión de cada artefacto regían la decisión `decision_id` (modo atribución §5.3). LookupError si no existe. _(línea 895)_
- `history(session, limit=…)` — Releases, decisiones governance.\*, activaciones programadas, propuestas de la app (con su validación) y el «Deshacer» disponible (volver al … _(línea 949)_
- `reset_for_tests()` _(línea 1014)_

**Internas** (empiezan con `_`): `_gov`, `_lint`, `_num`, `_versions_of`, `_auto_changelog`, `_impacts_changed`, `_x0_whatif`, `_fire_x0`, `_replay_whatif`, `_ledger_rows`, `_ledger_whatif`, `_committee_band`, `_ledger_committee`, `_order_amount_verdict`, `_ledger_orders`, `_nrs_compare`, `_focus_ids`, `_exposure`, `_shapes_section`, `_summary`, `_validation_output`, `_proposable_fields`

## Depende de

- [[core.__init__.py]] — importa `hot`, `impact`
- [[core.ai_usage.py]] — importa `ai_usage`
- [[core.decisions.py]] — importa `decisions`
- [[core.governance.py]] — importa `governance`
- [[core.governance_lint.py]] — importa `governance_lint`
- [[core.governance_preview.py]] — importa `governance_preview`
- [[core.governance_shadow.py]] — importa `governance_shadow`
- [[core.identity.py]] — importa `identity`
- [[core.world.py]] — importa `world`
- [[matrix.engine.py]] — importa `engine`
- [[ontology.db.py]] — importa `session_scope`

## Lo usan

- [[core.governance.py]] — lo importa
- [[core.governance_api.py]] — lo importa
- [[core.governance_preview.py]] — lo importa
- [[core.impls.py]] — lo importa

_Además lo importan 5 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_governance_activation.py]]
- [[tests.test_governance_flow.py]]
- [[tests.test_impl_registry.py]]
- [[tests.test_ledger_guard.py]]
- [[tests.test_replay_determinism.py]]
- [[tests.test_review_batch_g.py]]
