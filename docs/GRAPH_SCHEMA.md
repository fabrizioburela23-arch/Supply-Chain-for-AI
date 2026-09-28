# GRAPH SCHEMA (Phase 1 + Phase 2)

## Hechos (Phase 1, ontología bitemporal — `ontology/models.py`)
- `events` (append-only): event_type, object_id, target_id, payload, valid_from/valid_to, recorded_at, source,
  actor, source_id (Source), confidence.
- `objects`: id, type (Company, Tech, Policy, Country, Source, NewsItem, Factor, Thesis…), label, properties.
- `links`: source_id, target_id, rel_type (supply, fabrica, depende, affects, evidenced_by, reports_on…), weight,
  properties, valid_from/valid_to.
- `proposed_actions`, `alerts`, `insight_snapshots`.

## Conclusiones derivadas (Phase 2 — `research/models.py`)
- `research_claims` → `subject_entity_id` / `affected_entity_ids` apuntan a ids de `objects`/catálogo.
- `research_evidence` → `claim_id`, `source_id` (Source de la ontología).
- `claim_relations` → POTENTIALLY_CONTRADICTS entre claims.
- `agent_runs`, `research_jobs` → observabilidad.
Ver docs/CLAIM_MODEL.md.
