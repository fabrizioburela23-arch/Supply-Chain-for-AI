# MODEL ROUTING — sin acoplarse a un proveedor

`research/llm.py`: `LLMProvider {generate, structured_generate, tool_call}`; `CoreProvider` envuelve UN proveedor de
`core/ai.py` (claude|gemini|nvidia); `RoutedProvider` hace la cascada por agente; `FakeProvider` para tests.

## Configuración (variables de entorno en Railway)
```
RESEARCH_MODEL_DEFAULT=claude:deep,gemini,nvidia        # por defecto
RESEARCH_MODEL_FUNDAMENTAL=claude:claude-sonnet-5,gemini # razonamiento fuerte
RESEARCH_MODEL_NEWS=gemini,claude:fast                   # rápido y barato
RESEARCH_MODEL_TECHNICAL=claude:fast,gemini
```
Paso = `<proveedor>[:<modelo|deep|fast>]`; el primero que responde gana, el resto es fallback (queda registrado en
`agent_runs.validation.fallbacks`).

## Salida estructurada
`structured_generate` valida contra `AgentResearchResult` (Pydantic) + `check_refs` (solo ids E# del paquete).
Si falla: reintento con el error como feedback → siguiente proveedor → rechazo (`agent_runs.status=failed`).
Nunca se guarda JSON inválido.

## Costo
Tokens estimados (caracteres/4) × precio aproximado por familia → `est_cost_usd` (rotulado "estimado").
`RESEARCH_DAILY_BUDGET_USD` (2.0) · `RESEARCH_MAX_AGENTS_PER_JOB` (4) · `RESEARCH_DEDUPE_MINUTES` (30) ·
dedupe de eventos 24 h · QUICK por defecto en eventos · DEEP solo a pedido. `GET /api/research/budget`.
