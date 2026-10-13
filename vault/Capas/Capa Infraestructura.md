---
tipo: "capa"
capa: "Infraestructura"
archivos: 24
tags: ["capa/infraestructura", "tipo/capa"]
---

# Capa Infraestructura

> La base: server.py, IA en cascada y su gasto, PIN, HTTP saneado, reloj del servidor, service worker, sincronización.

**24 archivos · 15.760 líneas.** Volver al [[00 Mapa de Khipus]].

Variables de entorno: [[Índice de variables de entorno]].

## Archivos

- [[server.py]] — 6.059 líneas · Khipu Finance v1 Backend proxy ligero para el ecosistema de inteligencia de inversión.
- [[scripts.build_vault.py]] — 3.476 líneas · BÓVEDA DE OBSIDIAN + GRAFO DE CONOCIMIENTO del repo (2026-10-11).
- [[core.ai.py]] — 1.098 líneas · cascada multi-proveedor de IA (Claude → Gemini → NVIDIA).
- [[core.numbers.py]] — 856 líneas · guardián de CIFRAS (anti-alucinación numérica).
- [[core.decisions.py]] — 758 líneas · EL servicio de decisiones (docs/INFRA_OPERATIVA.md §2.2-§2.7; paso 6 del plan).
- [[core.ai_usage.py]] — 553 líneas · CONTROL DE GASTO DE IA (registro, límites y reporte).
- [[core.ledger.py]] — 313 líneas · sellado y verificación del libro (docs/INFRA_OPERATIVA.md §2.8; paso 6 del plan).
- [[core.ledger_ddl.py]] — 304 líneas · DDL idempotente de los registros que SOLO crecen (docs/INFRA_OPERATIVA.md §2.1, §4.3).
- [[engine.aispend.js]] — 283 líneas · 💰 GASTO DE IA (🩺 Sistema → pestaña "Gasto IA")
- [[sw.js]] — 277 líneas · Khipu Finance — Service Worker Servido por server.py en /sw.js con cabecera Service-Worker-Allowed: / CACHE va en la línea 6 (regla de despliegue #1: …
- [[core.pin.py]] — 260 líneas · verificación ÚNICA del PIN de operador (X-Trade-Pin).
- [[core.ops_check.py]] — 252 líneas · O1 (misión de reparación 2026-10-04): chequeo del sistema EN el servidor, guardado y consultable.
- [[core.identity.py]] — 227 líneas · QUIÉN actúa (docs/INFRA_OPERATIVA.md §1.2 paso 1, §2.2 y §8.1; paso 5 del plan).
- [[core.http.py]] — 189 líneas · llamadas upstream saneadas y límite de tasa (compartidos entre server, ontology y matrix).
- [[security_audit.py]] — 182 líneas · Khipu Finance (Fase 2H)
- [[core.ledger_api.py]] — 160 líneas · lectura del libro de decisiones: /api/ledger/\* (docs/INFRA_OPERATIVA.md §2.9; paso 6).
- [[engine.sync.js]] — 128 líneas · SINCRONIZACIÓN ENTRE DISPOSITIVOS (carteras, perfil, posiciones)
- [[core.scheduler.py]] — 116 líneas · tareas periódicas del SERVIDOR (misión de reparación 2026-10-04, R5).
- [[core.logjson.py]] — 81 líneas · O2 (misión de reparación 2026-10-04): logs estructurados.
- [[core.config.py]] — 80 líneas · variables de entorno compartidas entre server y ontology.
- [[core.agents_registry.py]] — 56 líneas · el registro de agentes del lado Python (limpieza 2026-10-11).
- [[core.tour.py]] — 39 líneas · el guion del recorrido de un minuto, lado Python (voz para Khipus OS, 2026-10-11).
- [[core.__init__.py]] — 13 líneas · helpers compartidos entre server.py (Flask) y ontology/ (agentes).
- [[scripts.__init__.py]] — 0 líneas

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| la usa | [[Capa Investigación]] | 22 |
| la usa | [[Capa Chat y agentes]] | 20 |
| la usa | [[Capa Ontología y grafo temporal]] | 19 |
| la usa | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 19 |
| la usa | [[Capa Comité]] | 15 |
| la usa | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 15 |
| la usa | [[Capa Dinero (carteras, trading, corretaje)]] | 15 |
| usa a | [[Capa Ontología y grafo temporal]] | 15 |
| usa a | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 12 |
| la usa | [[Capa MCP y API]] | 10 |
| usa a | [[Capa Chat y agentes]] | 7 |
| usa a | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 7 |
| usa a | [[Capa Dinero (carteras, trading, corretaje)]] | 7 |
| la usa | [[Capa Interfaz (Khipus OS)]] | 6 |
| usa a | [[Capa Investigación]] | 6 |
| usa a | [[Capa Interfaz (Khipus OS)]] | 5 |
| usa a | [[Capa MCP y API]] | 4 |
| la usa | [[Capa Voz]] | 1 |
| usa a | [[Capa Comité]] | 1 |
| usa a | [[Capa Voz]] | 1 |
