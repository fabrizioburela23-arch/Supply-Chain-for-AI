---
tipo: "capa"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
archivos: 27
tags: ["capa/datos-vivo", "tipo/capa"]
---

# Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)

> Todo lo que llega de afuera en vivo: precios, fundamentales, World Monitor, Space Monitor, noticias y el Dossier.

**27 archivos · 14.526 líneas.** Volver al [[00 Mapa de Khipus]].

## Archivos

- [[core.world.py]] — 2.133 líneas · WORLD MONITOR geopolítico: /api/world/\*.
- [[engine.spacemonitor.js]] — 1.350 líneas · SPACE MONITOR (pestaña 🚀 Espacio).
- [[core.company_data.py]] — 1.332 líneas · estados financieros anuales y perfil EN VIVO de cualquier empresa cotizada del mundo (Dossier, 2026-09-28).
- [[engine.worldmonitor.js]] — 1.326 líneas · WORLD MONITOR geopolítico (pestaña 🌐 Geopolítica).
- [[engine.fincard.js]] — 1.202 líneas · DOSSIER FINANCIERO de una empresa (Etapa G, 2026-07-11) Estilo investingvisuals que pidió Fabrizio: una tarjeta con small-multiples de indicadores …
- [[engine.globe.js]] — 1.037 líneas · MOTOR GLOBO UNIFICADO (Track A, Fase 1 del prompt 2026-08). Fusión de engine/geoglobe.js + engine/planetarium.js: el boilerplate Three.js …
- [[engine.crypto.js]] — 989 líneas · Pestaña ₿ Cripto (Fase 1 módulo de datos + Expediente). - Datos VIVOS: /api/crypto/\* (server → core/providers/coingecko.py). - Capa ESTÁTICA: …
- [[core.space.py]] — 640 líneas · SPACE MONITOR (pestaña 🚀 Espacio): /api/space2/\*.
- [[core.world_feeds.py]] — 632 líneas · fuentes OFICIALES nuevas del World Monitor (2026-10-05).
- [[core.quotes.py]] — 463 líneas · cotización cruda compartida (server rutas + agentes de alertas).
- [[core.geosit.py]] — 433 líneas · Sala de Situación geopolítica: /api/geo/\*.
- [[engine.geo_coords.js]] — 396 líneas · Coordenadas geográficas para los globos 3D (Khipu Finance) Los nodos NO traen lat/long: solo `country` (EEUU, Japon, "Estados Unidos (HQ Denver, …
- [[engine.termdata.js]] — 359 líneas · PANEL DE DATOS de la Terminal (feedback de Fabrizio: "te pedí que la terminal tuviera muchas más tablas" + "para muchas decía upstream 402 pero no …
- [[core.gdelt_events.py]] — 307 líneas · conflicto / protestas / sanciones EN VIVO desde la base de EVENTOS de GDELT 2.0 (archivos crudos cada 15 minutos, públicos y sin clave).
- [[engine.brief.js]] — 301 líneas · BRIEF MATINAL (te recibe con la inteligencia del día) Al abrir la app (una vez al día, descartable), un overlay NEXUS resume: el mayor chokepoint, la …
- [[core.country_geo.py]] — 222 líneas · coordenadas de referencia por PAÍS (la capital), para capas que solo dicen "qué país" (avisos de viaje del Departamento de Estado, cortes de …
- [[core.providers.base.py]] — 201 líneas · Phase 1 · M3: el contrato de los proveedores.
- [[core.gpr.py]] — 186 líneas · Índice de RIESGO GEOPOLÍTICO (GPR) de Caldara & Iacoviello (Junta de la Reserva Federal), EN VIVO y gratuito: https://www.matteoiacoviello.com/gpr.htm
- [[core.providers.market.py]] — 159 líneas · Phase 1 · M3: adapters de datos de mercado.
- [[core.news_feed.py]] — 151 líneas · NOTICIAS DE TU CARTERA, con fecha y sin repetir lo viejo.
- [[engine.live.js]] — 138 líneas · MODO EN VIVO (Etapa D, 2026-07) La app se mantiene relevante SOLA: 1) Latido de insights: cuando llegan precios nuevos, invalida el NRS y re-dibuja …
- [[core.live_caps.py]] — 127 líneas · capitalización EN VIVO de TODAS las cotizadas del grafo.
- [[core.providers.coingecko.py]] — 123 líneas · adapter de cripto (CoinGecko API v3, tier gratuito).
- [[core.live_fundamentals.py]] — 121 líneas · FUNDAMENTALES EN VIVO de TODAS las cotizadas del grafo.
- [[core.live_facts.py]] — 93 líneas · DATOS EN VIVO para toda llamada de IA.
- [[core.providers.news.py]] — 90 líneas · Phase 1 · M3: adapter de noticias.
- [[core.providers.__init__.py]] — 15 líneas · capa de proveedores de datos financieros (patrón adapter).

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| usa a | [[Capa Interfaz (Khipus OS)]] | 25 |
| usa a | [[Capa Infraestructura]] | 21 |
| la usa | [[Capa Interfaz (Khipus OS)]] | 20 |
| la usa | [[Capa Infraestructura]] | 17 |
| usa a | [[Capa Datos del catálogo]] | 10 |
| la usa | [[Capa Chat y agentes]] | 9 |
| la usa | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 9 |
| usa a | [[Capa Ontología y grafo temporal]] | 9 |
| la usa | [[Capa Dinero (carteras, trading, corretaje)]] | 8 |
| la usa | [[Capa MCP y API]] | 5 |
| usa a | [[Capa Chat y agentes]] | 5 |
| la usa | [[Capa Comité]] | 4 |
| la usa | [[Capa Investigación]] | 3 |
| la usa | [[Capa Ontología y grafo temporal]] | 3 |
| usa a | [[Capa Comité]] | 3 |
| la usa | [[Capa Voz]] | 2 |
| usa a | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 2 |
| usa a | [[Capa Investigación]] | 1 |
| usa a | [[Capa Voz]] | 1 |
