---
tipo: "capa"
capa: "Infraestructura"
archivos: 33
tags: ["capa/infraestructura", "tipo/capa"]
---

# Capa Infraestructura

> La base: server.py, IA en cascada y su gasto, PIN, HTTP saneado, reloj del servidor, service worker, sincronización.

**33 archivos · 19.639 líneas.** Volver al [[00 Mapa de Khipus]].

Variables de entorno: [[Índice de variables de entorno]].

## Archivos

- [[server.py]] — 6.423 líneas · Khipu Finance v1 Backend proxy ligero para el ecosistema de inteligencia de inversión.
- [[scripts.build_vault.py]] — 3.479 líneas · BÓVEDA DE OBSIDIAN + GRAFO DE CONOCIMIENTO del repo (2026-10-11).
- [[core.ai.py]] — 1.098 líneas · cascada multi-proveedor de IA (Claude → Gemini → NVIDIA).
- [[core.numbers.py]] — 869 líneas · guardián de CIFRAS (anti-alucinación numérica).
- [[core.governance.py]] — 846 líneas · EL registro de gobernanza (docs/INFRA_OPERATIVA.md §5.1-§5.4; paso 9 del plan).
- [[core.prices_store.py]] — 832 líneas · LA MEMORIA DE LOS NÚMEROS (docs/BRECHAS_V2.md bloque 2; ARQUITECTURA_V2 §9.1, §20.1 #1-#3).
- [[core.decisions.py]] — 794 líneas · EL servicio de decisiones (docs/INFRA_OPERATIVA.md §2.2-§2.7; paso 6 del plan).
- [[core.ledger.py]] — 683 líneas · sellado y verificación del libro (docs/INFRA_OPERATIVA.md §2.8; paso 6 del plan).
- [[core.ai_usage.py]] — 553 líneas · CONTROL DE GASTO DE IA (registro, límites y reporte).
- [[core.ledger_ddl.py]] — 308 líneas · DDL idempotente de los registros que SOLO crecen (docs/INFRA_OPERATIVA.md §2.1, §4.3).
- [[scripts.build_governance.py]] — 285 líneas · mantiene governance/manifest.json (docs/INFRA_OPERATIVA.md §5.1-§5.3; paso 9).
- [[engine.aispend.js]] — 283 líneas · 💰 GASTO DE IA (🩺 Sistema → pestaña "Gasto IA")
- [[sw.js]] — 277 líneas · Khipu Finance — Service Worker Servido por server.py en /sw.js con cabecera Service-Worker-Allowed: / CACHE va en la línea 6 (regla de despliegue #1: …
- [[scripts.build_shapes.py]] — 265 líneas · compila las formas SHACL a IR (docs/INFRA_OPERATIVA.md §3.3; paso 10).
- [[core.pin.py]] — 260 líneas · verificación ÚNICA del PIN de operador (X-Trade-Pin).
- [[core.ops_check.py]] — 252 líneas · O1 (misión de reparación 2026-10-04): chequeo del sistema EN el servidor, guardado y consultable.
- [[core.ledger_api.py]] — 232 líneas · lectura del libro de decisiones: /api/ledger/\* (docs/INFRA_OPERATIVA.md §2.9; paso 6).
- [[core.identity.py]] — 227 líneas · QUIÉN actúa (docs/INFRA_OPERATIVA.md §1.2 paso 1, §2.2 y §8.1; paso 5 del plan).
- [[core.instruments.py]] — 213 líneas · EMPRESA ≠ INSTRUMENTO (docs/BRECHAS_V2.md L3-13; ARQUITECTURA_V2 §3.2, §17.3, §20.1 #3).
- [[core.http.py]] — 189 líneas · llamadas upstream saneadas y límite de tasa (compartidos entre server, ontology y matrix).
- [[core.governance_preview.py]] — 182 líneas · "¿qué cambia para mí?" de una versión de artefacto ANTES de activarla (paso 12; pieza mínima del flujo de gobernanza §5.3 de docs/INFRA_OPERATIVA.md).
- [[security_audit.py]] — 182 líneas · Khipu Finance (Fase 2H)
- [[core.governance_api.py]] — 171 líneas · /api/governance/\* (docs/INFRA_OPERATIVA.md §5.1; paso 9). Nunca bajo /v1/\*.
- [[engine.sync.js]] — 128 líneas · SINCRONIZACIÓN ENTRE DISPOSITIVOS (carteras, perfil, posiciones)
- [[core.prices_api.py]] — 125 líneas · /api/prices/\* y /api/instruments/\* (BRECHAS bloque 2: la memoria de los números). Nunca /v1/\*.
- [[core.scheduler.py]] — 116 líneas · tareas periódicas del SERVIDOR (misión de reparación 2026-10-04, R5).
- [[scripts.fetch_ledger_anchor.py]] — 98 líneas · baja el ANCLA DIARIA pública del libro de decisiones y la guarda fuera de la base (docs/INFRA_OPERATIVA.md §2.8, paso 7, decisión D7). La corre el …
- [[core.logjson.py]] — 81 líneas · O2 (misión de reparación 2026-10-04): logs estructurados.
- [[core.config.py]] — 80 líneas · variables de entorno compartidas entre server y ontology.
- [[core.agents_registry.py]] — 56 líneas · el registro de agentes del lado Python (limpieza 2026-10-11).
- [[core.tour.py]] — 39 líneas · el guion del recorrido de un minuto, lado Python (voz para Khipus OS, 2026-10-11).
- [[core.__init__.py]] — 13 líneas · helpers compartidos entre server.py (Flask) y ontology/ (agentes).
- [[scripts.__init__.py]] — 0 líneas

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| la usa | [[Capa Ontología y grafo temporal]] | 28 |
| la usa | [[Capa Chat y agentes]] | 23 |
| la usa | [[Capa Investigación]] | 23 |
| usa a | [[Capa Ontología y grafo temporal]] | 23 |
| la usa | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 22 |
| la usa | [[Capa Dinero (carteras, trading, corretaje)]] | 22 |
| la usa | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 20 |
| la usa | [[Capa Comité]] | 16 |
| usa a | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 15 |
| la usa | [[Capa MCP y API]] | 10 |
| usa a | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 9 |
| la usa | [[Capa Interfaz (Khipus OS)]] | 8 |
| usa a | [[Capa Dinero (carteras, trading, corretaje)]] | 8 |
| usa a | [[Capa Chat y agentes]] | 7 |
| usa a | [[Capa Investigación]] | 6 |
| usa a | [[Capa Interfaz (Khipus OS)]] | 5 |
| usa a | [[Capa MCP y API]] | 4 |
| la usa | [[Capa Datos del catálogo]] | 1 |
| la usa | [[Capa Voz]] | 1 |
| usa a | [[Capa Comité]] | 1 |
| usa a | [[Capa Voz]] | 1 |
