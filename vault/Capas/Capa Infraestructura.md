---
tipo: "capa"
capa: "Infraestructura"
archivos: 47
tags: ["capa/infraestructura", "tipo/capa"]
---

# Capa Infraestructura

> La base: server.py, IA en cascada y su gasto, PIN, HTTP saneado, reloj del servidor, service worker, sincronización.

**47 archivos · 26.522 líneas.** Volver al [[00 Mapa de Khipus]].

Variables de entorno: [[Índice de variables de entorno]].

## Archivos

- [[server.py]] — 4.945 líneas · Khipu Finance v1 Backend proxy ligero para el ecosistema de inteligencia de inversión.
- [[scripts.build_vault.py]] — 3.492 líneas · BÓVEDA DE OBSIDIAN + GRAFO DE CONOCIMIENTO del repo (2026-10-11).
- [[core.replay.py]] — 1.473 líneas · REPETIR UNA DECISIÓN (docs/INFRA_OPERATIVA.md §5.6; paso 24 del plan).
- [[core.ai.py]] — 1.196 líneas · cascada multi-proveedor de IA (Claude → Gemini → NVIDIA).
- [[core.governance.py]] — 1.109 líneas · EL registro de gobernanza (docs/INFRA_OPERATIVA.md §5.1-§5.4; paso 9 del plan).
- [[core.governance_flow.py]] — 1.016 líneas · FLUJO DE GOBERNANZA COMPLETO (docs/INFRA_OPERATIVA.md §5.3; paso 25 del plan).
- [[core.decisions.py]] — 902 líneas · EL servicio de decisiones (docs/INFRA_OPERATIVA.md §2.2-§2.7; paso 6 del plan).
- [[core.numbers.py]] — 869 líneas · guardián de CIFRAS (anti-alucinación numérica).
- [[core.prices_store.py]] — 867 líneas · LA MEMORIA DE LOS NÚMEROS (docs/BRECHAS_V2.md bloque 2; ARQUITECTURA_V2 §9.1, §20.1 #1-#3).
- [[core.decision_sites.py]] — 816 líneas · decisiones del COMITÉ, la INVESTIGACIÓN, las PROPUESTAS y las ALERTAS (docs/INFRA_OPERATIVA.md §2.5; pasos 18 y 19 del plan).
- [[core.context_engine.py]] — 797 líneas · EL motor de contexto (ARQUITECTURA_V2 §13; BRECHAS bloque 4: L4-01, L4-05, L4-10).
- [[core.ledger.py]] — 729 líneas · sellado y verificación del libro (docs/INFRA_OPERATIVA.md §2.8; paso 6 del plan).
- [[core.ai_usage.py]] — 686 líneas · CONTROL DE GASTO DE IA (registro, límites y reporte).
- [[core.countries.py]] — 451 líneas · UNA tabla de países: ISO-2 ↔ clave del catálogo ↔ nombre ES/EN ↔ región (lote 2026-10-14).
- [[core.ledger_guard.py]] — 451 líneas · GUARDIA DE PROYECCIONES «sin decisión no hay cambio» (docs/INFRA_OPERATIVA.md §2.1; paso 22).
- [[core.instruments.py]] — 410 líneas · EMPRESA ≠ INSTRUMENTO (docs/BRECHAS_V2.md L3-13; ARQUITECTURA_V2 §3.2, §17.3, §20.1 #3).
- [[core.governance_api.py]] — 381 líneas · /api/governance/\* (docs/INFRA_OPERATIVA.md §5.1; paso 9). Nunca bajo /v1/\*.
- [[core.ledger_ddl.py]] — 374 líneas · DDL idempotente de los registros que SOLO crecen (docs/INFRA_OPERATIVA.md §2.1, §4.3).
- [[core.ledger_api.py]] — 359 líneas · lectura del libro de decisiones: /api/ledger/\* (docs/INFRA_OPERATIVA.md §2.9; paso 6).
- [[core.impls.py]] — 349 líneas · IMPLEMENTACIONES RETENIDAS (docs/INFRA_OPERATIVA.md §5.2 «Implementaciones retenidas»; paso 24).
- [[core.import_normalize.py]] — 325 líneas · normalización de la ficha khipus.company/1 a la convención interna (E2.2).
- [[core.ai_calls.py]] — 317 líneas · registro append-only de CADA pedido a la IA (docs/INFRA_OPERATIVA.md §2.6, paso 21; GV-11).
- [[core.retention.py]] — 312 líneas · PURGA POR RETENCIÓN del libro (docs/INFRA_OPERATIVA.md §2.7; paso 26; decisión D3).
- [[sw.js]] — 296 líneas · Khipu Finance — Service Worker Servido por server.py en /sw.js con cabecera Service-Worker-Allowed: / CACHE va en la línea 6 (regla de despliegue #1: …
- [[engine.aispend.js]] — 286 líneas · 💰 GASTO DE IA (🩺 Sistema → pestaña "Gasto IA")
- [[core.governance_lint.py]] — 270 líneas · EL lint de los artefactos de gobernanza (docs/INFRA_OPERATIVA.md §5.2; pasos 9 y 25).
- [[scripts.build_shapes.py]] — 265 líneas · compila las formas SHACL a IR (docs/INFRA_OPERATIVA.md §3.3; paso 10).
- [[core.pin.py]] — 260 líneas · verificación ÚNICA del PIN de operador (X-Trade-Pin).
- [[core.ops_check.py]] — 257 líneas · O1 (misión de reparación 2026-10-04): chequeo del sistema EN el servidor, guardado y consultable.
- [[core.celestrak.py]] — 255 líneas · satélites reales (CelesTrak) para el Space Monitor y el texto de Khipu.
- [[core.identity.py]] — 227 líneas · QUIÉN actúa (docs/INFRA_OPERATIVA.md §1.2 paso 1, §2.2 y §8.1; paso 5 del plan).
- [[scripts.build_governance.py]] — 226 líneas · mantiene governance/manifest.json (docs/INFRA_OPERATIVA.md §5.1-§5.3; paso 9).
- [[core.governance_preview.py]] — 191 líneas · "¿qué cambia para mí?" de una versión de artefacto ANTES de activarla (paso 12; pieza mínima del flujo de gobernanza §5.3 de docs/INFRA_OPERATIVA.md).
- [[core.http.py]] — 189 líneas · llamadas upstream saneadas y límite de tasa (compartidos entre server, ontology y matrix).
- [[security_audit.py]] — 182 líneas · Khipu Finance (Fase 2H)
- [[core.governance_shadow.py]] — 179 líneas · FORMAS PROPUESTAS EN SOMBRA junto a las vigentes (docs/INFRA_OPERATIVA.md §5.3; paso 25).
- [[engine.sync.js]] — 128 líneas · SINCRONIZACIÓN ENTRE DISPOSITIVOS (carteras, perfil, posiciones)
- [[core.prices_api.py]] — 125 líneas · /api/prices/\* y /api/instruments/\* (BRECHAS bloque 2: la memoria de los números). Nunca /v1/\*.
- [[core.scheduler.py]] — 116 líneas · tareas periódicas del SERVIDOR (misión de reparación 2026-10-04, R5).
- [[scripts.fetch_ledger_anchor.py]] — 98 líneas · baja el ANCLA DIARIA pública del libro de decisiones y la guarda fuera de la base (docs/INFRA_OPERATIVA.md §2.8, paso 7, decisión D7). La corre el …
- [[core.config.py]] — 82 líneas · variables de entorno compartidas entre server y ontology.
- [[core.logjson.py]] — 81 líneas · O2 (misión de reparación 2026-10-04): logs estructurados.
- [[scripts.build_impl_goldens.py]] — 75 líneas · salidas DORADAS de las implementaciones retenidas (core/impls.py; INFRA §5.2, paso 24).
- [[core.agents_registry.py]] — 56 líneas · el registro de agentes del lado Python (limpieza 2026-10-11).
- [[core.tour.py]] — 39 líneas · el guion del recorrido de un minuto, lado Python (voz para Khipus OS, 2026-10-11).
- [[core.__init__.py]] — 13 líneas · helpers compartidos entre server.py (Flask) y ontology/ (agentes).
- [[scripts.__init__.py]] — 0 líneas

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| la usa | [[Capa Ontología y grafo temporal]] | 48 |
| usa a | [[Capa Ontología y grafo temporal]] | 38 |
| la usa | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 35 |
| la usa | [[Capa Chat y agentes]] | 31 |
| la usa | [[Capa Dinero (carteras, trading, corretaje)]] | 29 |
| la usa | [[Capa Investigación]] | 27 |
| la usa | [[Capa MCP y API]] | 23 |
| la usa | [[Capa Comité]] | 22 |
| la usa | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 22 |
| usa a | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 19 |
| usa a | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 15 |
| la usa | [[Capa Interfaz (Khipus OS)]] | 13 |
| usa a | [[Capa Dinero (carteras, trading, corretaje)]] | 11 |
| la usa | [[Capa Voz]] | 7 |
| usa a | [[Capa Chat y agentes]] | 7 |
| usa a | [[Capa Investigación]] | 7 |
| usa a | [[Capa Comité]] | 6 |
| usa a | [[Capa Interfaz (Khipus OS)]] | 6 |
| usa a | [[Capa MCP y API]] | 4 |
| la usa | [[Capa Datos del catálogo]] | 2 |
| usa a | [[Capa Voz]] | 2 |
