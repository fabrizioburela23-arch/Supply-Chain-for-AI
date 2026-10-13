---
tipo: "capa"
capa: "Voz"
archivos: 4
tags: ["capa/voz", "tipo/capa"]
---

# Capa Voz

> Khipu por voz: ElevenLabs (servidor y navegador) y el orbe.

**4 archivos · 5.090 líneas.** Volver al [[00 Mapa de Khipus]].

## Archivos

- [[engine.voice.js]] — 2.819 líneas · Khipu, el asistente de voz de Khipu Finance Cliente WebSocket de ElevenLabs Agents (Conversational AI). Khipu es el "Jarvis de las finanzas": escucha …
- [[core.voice_agent.py]] — 1.050 líneas · Khipu (voz) ↔ ElevenLabs Agents Platform (oct-2026).
- [[core.voice_api.py]] — 825 líneas · Voz de Khipu — rutas /api/voice/\* (G5-05, lote I4: salieron de server.py SIN cambiar comportamiento).
- [[engine.orb.js]] — 396 líneas · BixbyOrb: el orbe de voz de Khipu.

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| usa a | [[Capa Interfaz (Khipus OS)]] | 8 |
| usa a | [[Capa Infraestructura]] | 7 |
| la usa | [[Capa Interfaz (Khipus OS)]] | 5 |
| usa a | [[Capa Datos del catálogo]] | 3 |
| usa a | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 3 |
| la usa | [[Capa Infraestructura]] | 2 |
| usa a | [[Capa Chat y agentes]] | 2 |
| usa a | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 2 |
| la usa | [[Capa Chat y agentes]] | 1 |
| la usa | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 1 |
| usa a | [[Capa Comité]] | 1 |
| usa a | [[Capa Dinero (carteras, trading, corretaje)]] | 1 |
| usa a | [[Capa Investigación]] | 1 |
| usa a | [[Capa Ontología y grafo temporal]] | 1 |
