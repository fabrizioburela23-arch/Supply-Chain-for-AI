---
tipo: "capa"
capa: "Dinero (carteras, trading, corretaje)"
archivos: 13
tags: ["capa/dinero", "tipo/capa"]
---

# Capa Dinero (carteras, trading, corretaje)

> Carteras, órdenes y corretaje multi-cliente con Alpaca. Regla de oro: toda orden pasa por preview → confirmación humana.

**13 archivos · 7.797 líneas.** Volver al [[00 Mapa de Khipus]].

## Archivos

- [[brokerage.service.py]] — 1.530 líneas · lógica del corretaje multi-cliente (CONTRATO COMPARTIDO).
- [[engine.portfolios.js]] — 1.369 líneas · 🧪 CARTERAS SIMULADAS (paper trading local)
- [[core.portfolio_ai.py]] — 1.266 líneas · ASISTENTE DE CARTERAS (💼 Carteras → 🤖 Asistente).
- [[engine.clients.js]] — 1.060 líneas · 👥 CLIENTES E INVERSIÓN (corretaje multi-cliente vía Alpaca).
- [[core.portfolio_reports_api.py]] — 468 líneas · /api/portfolio-report/\* y /api/news/portfolio.
- [[brokerage.risk.py]] — 439 líneas · controles de riesgo PRE-orden por cliente.
- [[brokerage.api.py]] — 419 líneas · blueprint /api/brokerage/\* (corretaje multi-cliente).
- [[engine.pfreports.js]] — 414 líneas · 📄 REPORTES · 📰 NOTICIAS · 💬 PREGÚNTALE A TU CARTERA (secciones de Comité → 💼 Mi cartera; las monta engine/pfcommittee.js)
- [[brokerage.alpaca.py]] — 256 líneas · cliente HTTP mínimo de Alpaca (Trading API v2 + OAuth).
- [[core.portfolio_report.py]] — 227 líneas · REPORTE DE CARTERA (a pedido, diario, semanal o mensual).
- [[brokerage.models.py]] — 200 líneas · tablas del corretaje multi-cliente.
- [[brokerage.crypto.py]] — 135 líneas · cifrado de credenciales de clientes (Fernet).
- [[brokerage.__init__.py]] — 14 líneas · corretaje MULTI-CLIENTE vía Alpaca (Phase 3, 2026-09-30).

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| usa a | [[Capa Infraestructura]] | 15 |
| usa a | [[Capa Interfaz (Khipus OS)]] | 11 |
| usa a | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 8 |
| la usa | [[Capa Comité]] | 7 |
| la usa | [[Capa Infraestructura]] | 7 |
| la usa | [[Capa Interfaz (Khipus OS)]] | 6 |
| la usa | [[Capa MCP y API]] | 6 |
| usa a | [[Capa Ontología y grafo temporal]] | 6 |
| usa a | [[Capa Chat y agentes]] | 4 |
| usa a | [[Capa Comité]] | 3 |
| usa a | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 3 |
| la usa | [[Capa Chat y agentes]] | 2 |
| la usa | [[Capa Ontología y grafo temporal]] | 2 |
| usa a | [[Capa Datos del catálogo]] | 2 |
| usa a | [[Capa Investigación]] | 2 |
| la usa | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 1 |
