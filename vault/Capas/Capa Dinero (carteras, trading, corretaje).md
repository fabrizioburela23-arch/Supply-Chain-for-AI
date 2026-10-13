---
tipo: "capa"
capa: "Dinero (carteras, trading, corretaje)"
archivos: 16
tags: ["capa/dinero", "tipo/capa"]
---

# Capa Dinero (carteras, trading, corretaje)

> Carteras, órdenes y corretaje multi-cliente con Alpaca. Regla de oro: toda orden pasa por preview → confirmación humana.

**16 archivos · 10.615 líneas.** Volver al [[00 Mapa de Khipus]].

## Archivos

- [[brokerage.service.py]] — 2.340 líneas · lógica del corretaje multi-cliente (CONTRATO COMPARTIDO).
- [[engine.portfolios.js]] — 1.371 líneas · 🧪 CARTERAS SIMULADAS (paper trading local)
- [[core.portfolio_ai.py]] — 1.298 líneas · ASISTENTE DE CARTERAS (💼 Carteras → 🤖 Asistente).
- [[engine.clients.js]] — 1.060 líneas · 👥 CLIENTES E INVERSIÓN (corretaje multi-cliente vía Alpaca).
- [[core.trading_agent.py]] — 810 líneas · Agente de trading de la cuenta de la casa — /api/trade/agent/\* (G5-05, lote I4: salió de server.py SIN cambiar comportamiento).
- [[brokerage.risk.py]] — 651 líneas · controles de riesgo PRE-orden por cliente.
- [[engine.app_trade_panel.js]] — 608 líneas · Professional Trade Panel
- [[core.portfolio_reports_api.py]] — 468 líneas · /api/portfolio-report/\* y /api/news/portfolio.
- [[brokerage.api.py]] — 436 líneas · blueprint /api/brokerage/\* (corretaje multi-cliente).
- [[engine.pfreports.js]] — 414 líneas · 📄 REPORTES · 📰 NOTICIAS · 💬 PREGÚNTALE A TU CARTERA (secciones de Comité → 💼 Mi cartera; las monta engine/pfcommittee.js)
- [[engine.trade.js]] — 274 líneas · TRADING COMPARTIDO del navegador (lote I4, G5-07: salió TAL CUAL de engine/voice.js). Lo usan la voz (engine/voice.js: place_order / …
- [[brokerage.alpaca.py]] — 256 líneas · cliente HTTP mínimo de Alpaca (Trading API v2 + OAuth).
- [[core.portfolio_report.py]] — 246 líneas · REPORTE DE CARTERA (a pedido, diario, semanal o mensual).
- [[brokerage.models.py]] — 234 líneas · tablas del corretaje multi-cliente.
- [[brokerage.crypto.py]] — 135 líneas · cifrado de credenciales de clientes (Fernet).
- [[brokerage.__init__.py]] — 14 líneas · corretaje MULTI-CLIENTE vía Alpaca (Phase 3, 2026-09-30).

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| usa a | [[Capa Infraestructura]] | 29 |
| usa a | [[Capa Interfaz (Khipus OS)]] | 20 |
| la usa | [[Capa Interfaz (Khipus OS)]] | 12 |
| la usa | [[Capa Infraestructura]] | 11 |
| la usa | [[Capa Comité]] | 8 |
| usa a | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 8 |
| usa a | [[Capa Ontología y grafo temporal]] | 7 |
| la usa | [[Capa MCP y API]] | 6 |
| usa a | [[Capa Chat y agentes]] | 5 |
| la usa | [[Capa Chat y agentes]] | 4 |
| usa a | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 4 |
| usa a | [[Capa Datos del catálogo]] | 3 |
| usa a | [[Capa Comité]] | 3 |
| la usa | [[Capa Ontología y grafo temporal]] | 2 |
| la usa | [[Capa Voz]] | 2 |
| usa a | [[Capa Investigación]] | 2 |
| la usa | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 1 |
