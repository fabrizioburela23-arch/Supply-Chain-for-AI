# CLAIM MODEL — tres capas que NO se mezclan

| Capa | Dónde | Quién escribe |
|---|---|---|
| RAW DATA | proveedores (`core/providers`, `core/company_data`) | nadie la modifica |
| GRAPH FACTS | `events` / `objects` / `links` (ontología bitemporal) | Acciones auditadas, ingesta, humanos |
| DERIVED CLAIMS | `research_claims` / `research_evidence` / `claim_relations` | agentes (Phase 2) |

## Claim (`research_claims`)
`id, job_id, run_id, agent_id, agent_type, agent_version, subject_entity_id, predicate (UPPER_SNAKE), object,
claim_type (observation|risk|opportunity|forecast), topic (vocabulario cerrado), stance (positive|negative|neutral|mixed),
statement_es/en, reasoning_summary (auditable, NO chain-of-thought), horizon, depth, valid_from, valid_to,
confidence, confidence_components, affected_entity_ids, falsifiers, status (active|superseded|retracted), model,
prompt_version, created_at`.

Responde: quién (agente/versión/modelo/prompt), cuándo, con qué evidencia, qué afecta, qué horizonte, qué
confianza (y por qué) y **qué la refutaría** (`falsifiers`, obligatorio).

## Evidence (`research_evidence`)
`id, claim_id, stance (supporting|counter), context_ref (E#), source_id (Source de la ontología), source_type
(financials|market|news|catalog|web|graph), source_reference (URL o ref interna), title, excerpt, published_at,
retrieved_at, relevance, reliability`. **Sin evidencia de apoyo no hay claim** (se descarta).

## Horizontes
INTRADAY · SHORT_TERM (≤3 meses) · MEDIUM_TERM (3-12) · LONG_TERM (1-5 años) · STRUCTURAL (>5). `valid_to` se
deriva del horizonte. Claims de horizontes distintos **coexisten** y no se consideran contradicción.

## Confianza (`research/confidence.py`, método conf-v2)

**conf-v2 (misión de reparación 2026-10-04, C9).** `source_type` vocabulario:
financials · market · news · web · filing · earnings · catalog · graph ·
**computed** (ratios/pares calculados por Khipus; antes 'analysis'). Reglas
nuevas: toda referencia `khipus:*` (catálogo, grafo, ratios, pares) cuenta como
UNA sola familia de referencia interna; lo `computed` no suma independencia
(sus insumos ya cuentan); una conclusión con cifras de dinero y SIN ninguna
fuente primaria externa (http) queda topada en 0.5. Las claims conf-v1 anteriores
no se recalculan (append-only): `confidence_components.method` dice cuál es.
source_quality 30% · independence 20% · recency 15% · agreement 15% · agent_certainty 10% · completeness 10%.
Una sola referencia → tope 0.6; máximo 0.95. Se guardan componentes, pesos y topes.

## Contradicciones (`claim_relations`)
Regla v1: misma entidad + mismo tema + mismo horizonte + posturas opuestas + agentes distintos →
`POTENTIALLY_CONTRADICTS`. No se resuelve (Phase 3 · Investment Committee).

## Memoria
Nueva claim del mismo agente/tema/horizonte → la anterior pasa a `superseded`. El ContextBuilder recupera solo
las últimas claims activas del mismo agente (retrieval selectivo, no historial de conversación).
