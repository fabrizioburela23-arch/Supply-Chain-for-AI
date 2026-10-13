---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/replay.py"
lenguaje: "python"
lineas: 1436
aliases: ["core/replay.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/replay.py

> Módulo · capa [[Capa Infraestructura]] · 1.436 líneas · `core/replay.py`

## Para qué sirve

REPETIR UNA DECISIÓN (docs/INFRA_OPERATIVA.md §5.6; paso 24 del plan).

## API pública

- `kind_label(kind, lang=…)` _(línea 173)_
- `replayable_kind(kind)` — ¿Tiene núcleo determinista que se pueda repetir? (las puertas y la IA se verifican en todas). _(línea 178)_
- `release_artifacts(session, d)` — (arts, info) del release que REGÍA la decisión. info = {source, release_hash_ok, missing, fallback}. _(línea 358)_
- `impls_clean(v)` _(línea 744)_
- `replay(decision_id, mode=…, full=…, record=…, principal=…, use_cache=…)` — El replay (modo 'audit'). → dict (ver docstring del módulo). LookupError si la decisión no existe; ValueError con un modo que no es … _(línea 1079)_
- `cache_clear()` _(línea 1216)_
- `why(session, decision_id, full=…)` — Explicación de una decisión: quién (tipo; el id solo con PIN), qué, cuándo, con qué conocimiento (versión del grafo, reglas por artefacto), … _(línea 1224)_
- `recent(session, kind=…, principal=…, principal_kind=…, since=…, until=…, limit=…, full=…)` — Lista para ⚖ Auditoría: decisiones recientes con su etiqueta ES/EN y si tienen cálculo repetible. _(línea 1292)_
- `kinds_catalog()` _(línea 1328)_
- `sample(n=…, hours=…, force=…)` — Repite la muestra y deja UNA audit.replay (system:ledger_replay_sample) con los conteos. → resumen. _(línea 1358)_
- `sample_job(force=…)` — `system:ledger_replay_sample` (el reloj mira cada hora; corre UNA vez por día UTC). _(línea 1400)_
- `status(engine=…)` — Para el 🩺: la última muestra (de la base) y si hubo 'differs'. _(línea 1410)_

**Internas** (empiezan con `_`): `_Run`, `_blob`, `_mf`, `_need_params`, `_inputs_lost`, `_iso`, `_integrity`, `_art_body`, `_generation_of`, `_lineage_now`, `_graph`, `_view_check`, `_whatif_world`, `_output`, `_whatif_compare`, `_replay_whatif_shock`, `_replay_whatif_fire`, `_committee_legacy_inputs`, `_replay_committee`, `_replay_order`, `_replay_validate`, `_ir_for`, `_replay_gates`, `_replay_ai`, `_explain`, `_run`, `_redact_steps`, `_seen`, `_already_logged`, `_record`, `_sample_ids`, `_ran_today`, `_reset_for_tests`

## Depende de

- [[brokerage.risk.py]] — importa `(dinámico: brokerage.risk)`
- [[core.__init__.py]] — importa `asof`, `engine`, `focus`, `graph_core`, `impact`, `report`
- [[core.ai_calls.py]] — importa `ai_calls`
- [[core.decision_sites.py]] — importa `clean`
- [[core.decisions.py]] — importa `KINDS`, `decisions`
- [[core.governance.py]] — importa `governance`
- [[core.governance_preview.py]] — importa `governance_preview`
- [[core.identity.py]] — importa `identity`
- [[core.impls.py]] — importa `impls`
- [[core.ledger.py]] — importa `ledger`
- [[core.numbers.py]] — importa `(dinámico: core.numbers)`
- [[matrix.api.py]] — importa `MAGNITUDE_MAX`
- [[matrix.engine.py]] — importa `engine`
- [[ontology.bitemporal.py]] — importa `bitemporal`
- [[ontology.bulk_import.py]] — importa `(dinámico: ontology.bulk_import)`
- [[ontology.db.py]] — importa `_get_engine`, `get_session_factory`, `ontology_available`, `session_scope`
- [[ontology.service.py]] — importa `_parse_dt`
- [[research.committee.py]] — importa `(dinámico: research.committee)`
- [[research.outcomes.py]] — importa `is_us_listing`

## Lo usan

- [[core.ledger_api.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `replay_decision` → [[API herramientas MCP]]

_Además lo importan 3 pruebas (lista abajo)._

**Rutas que nombra y no existen en el servidor** (¿restos viejos?): `/api/hot/scenario`, `/api/hot/scenario_pnl`

## Pruebas que lo cubren

- [[tests.test_cierre_defectos.py]]
- [[tests.test_cierre_infra.py]]
- [[tests.test_impl_registry.py]]
- [[tests.test_replay_determinism.py]]
- [[tests.test_rutas_acceso_decision.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (h) — PASO 24 - REPETIR DECISIONES (replay), IMPLEMENTACIONES RETENIDAS]]
