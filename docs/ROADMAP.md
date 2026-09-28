# ROADMAP — Investment Operating System

Live Economic Graph (**Phase 1 ✅**, docs/ROADMAP_PHASE1.md)
→ **Agent Research Swarm (Phase 2 ✅ v1, esta entrega)**
→ Investment Committee (Phase 3) → Investor Policy → Portfolio Intelligence → Risk Engine → Strategy Engine
→ Broker Execution → API/MCP → Agentic Investment System.

## Phase 2 — estado
- [x] Claim + Evidence schema, horizontes, confianza conf-v1 con componentes
- [x] Interfaz Agent + 8 agentes (Fundamental, News, Technical, SupplyChain, Geopolitical, Macro, Crypto, RiskObservation)
- [x] ContextBuilder con límites y paquete de evidencia numerado; memoria selectiva
- [x] LLMProvider + routing por agente + fallback + salida estructurada con reintento/rechazo
- [x] Router de eventos + relevancia por grafo con límites + dedupe 24 h
- [x] Contradicciones POTENTIALLY_CONTRADICTS; supersesión de claims
- [x] Observabilidad (agent_runs), control de costo (presupuesto diario, dedupe, profundidades)
- [x] UI: 🔬 Investigación IA (ficha del mapa, X-Ray, comando `<TICKER> RESEARCH`), ¿Por qué?, síntesis, actividad real
- [ ] Contradicciones semánticas (más allá de la regla tema/horizonte/postura)
- [ ] Más eventos automáticos: resultados trimestrales (EARNINGS), anomalías de precio, factores disparados
- [ ] Evidencia de filings SEC para FundamentalAgent
- [ ] Calibración de la confianza con resultados reales (Phase 3)

## Fuera de alcance (fases posteriores)
Comité de inversión completo, recomendaciones personalizadas, BUY/SELL, optimización de cartera, ejecución,
trading automático, MCP trading, decisiones autónomas.
