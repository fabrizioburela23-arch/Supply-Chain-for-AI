# AGENT ARCHITECTURE — Phase 2 · Agent Research Swarm

Código: `research/` (servidor) + `engine/research.js` (UI). Tablas: `research_*`, `agent_runs`.

## Loop
```
LIVE DATA → EVENT → GRAPH UPDATE → RELEVANCE (router) → SPECIALIZED AGENTS
→ CLAIMS → EVIDENCE / COUNTER-EVIDENCE → GRAPH (research_*) → USER
```

## Interfaz común (`research/agents/base.py`)
`Agent {agent_id, agent_type, version, capabilities[], permitted_tools[], subscribed_events[], route, focus, prompt_version}`.
`run(context, provider) → (AgentResearchResult validado, meta)`. El agente **no toca la base**: el runner persiste.

| Agente | Lee (context.AGENT_NEEDS) | Eventos que lo activan | Horizontes típicos |
|---|---|---|---|
| FundamentalAgent | estados anuales, perfil de mercado, noticias, catálogo, grafo | USER_RESEARCH, EARNINGS, FILING, GUIDANCE_CHANGE | MEDIUM→STRUCTURAL |
| NewsAgent | noticias, catálogo | USER_RESEARCH, NEWS, EARNINGS, PRICE_ANOMALY | SHORT, MEDIUM |
| TechnicalAgent | perfil, indicadores de precio calculados (sin IA), noticias | USER_RESEARCH, PRICE_ANOMALY, CRYPTO_EVENT | INTRADAY, SHORT |
| SupplyChainAgent | subgrafo, catálogo, noticias, perfil | USER_RESEARCH, GEOPOLITICAL_EVENT, SUPPLY_SHOCK, FACTOR_FIRED | MEDIUM→STRUCTURAL |
| GeopoliticalAgent | catálogo, grafo, noticias | GEOPOLITICAL_EVENT, SANCTION, FACTOR_FIRED | SHORT, MEDIUM, STRUCTURAL |
| MacroAgent | catálogo, grafo, noticias | MACRO_EVENT, GEOPOLITICAL_EVENT, FACTOR_FIRED | MEDIUM, LONG |
| CryptoAgent | noticias, catálogo | CRYPTO_EVENT | SHORT, MEDIUM |
| RiskObservationAgent | perfil, grafo, noticias, catálogo | USER_RESEARCH, EARNINGS, PRICE_ANOMALY | SHORT→LONG |

Por defecto un pedido del usuario corre **fundamental, news, technical, supply_chain** (`RESEARCH_MAX_AGENTS_PER_JOB`=4).

## Qué pueden escribir
Solo `research_claims`, `research_evidence`, `claim_relations`, `agent_runs` y registrar (idempotente) la `Source`
que citan. **Nunca**: eventos de hechos, datos de mercado, catálogo, documentos fuente, identidades canónicas.

## Piezas
- **ContextBuilder** (`research/context.py`): subgrafo acotado (max_nodes/max_depth por profundidad), datos en vivo,
  noticias, memoria selectiva (últimas 5 claims activas del mismo agente) y un **paquete de evidencia numerado E1..En** —
  lo único que el modelo puede citar.
- **Router / relevancia** (`research/router.py`): evento → entidades (semillas + BFS por el grafo con `max_depth`,
  `max_nodes`, `relationship_types`, `min_weight`) → agentes suscritos → jobs QUICK. Dedupe 24 h por `event_key`.
- **Runner** (`research/runner.py`): job → por agente: contexto → modelo → validación → confianza → persistencia →
  contradicciones → síntesis. Cada agente es un `AgentRun` observable.
- **Eventos automáticos**: la ingesta de noticias (`POST /api/ontology/ingest/news`) dispara `NEWS` si
  `RESEARCH_AUTO_EVENTS=on` (apagado por defecto por costo). `POST /api/research/events` acepta cualquier evento.

## Profundidad
QUICK (automática, 6 vecinos, 4 noticias) · STANDARD (12 vecinos, 8 noticias) · DEEP (25 vecinos, 12 noticias,
búsqueda web Tavily; solo a pedido explícito). Cada claim guarda su `depth`.

## API
`/api/research/agents · jobs (POST) · jobs/<id> · entity/<id> · claims/<id> (¿por qué?) · activity · budget · events (POST)`.
