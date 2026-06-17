# Khipu Finance — CLAUDE.md

Bloomberg Terminal + AI para semiconductores, IA y espacio.

## Arquitectura crítica

- `app.html` (6800+ líneas): toda la UI. Inline script principal líneas 1432–6439, segundo bloque 6479–6780
- `server.py` (730+ líneas): Flask proxy + JWT auth + VaR/CVaR
- `engine/`: graph3d.js (Three.js), hypergraph.js, voice.js (Bixby), secondbrain.js
- `sim/`: mirofish_client.js, scenario_builder.js (5 presets geopolíticos)
- `nodes/`: nodes_expand.js (100), nodes_expand2.js (173+), nodes_spacex.js (40) + links
- `rag/rag_server.py`: ChromaDB microservicio puerto 5051

## Convenciones de datos críticas

**Links en RAW_LINKS**: array `[s, t, w, rel, type]` — los objetos `{s,t,type}` de links_expand.js se convierten en el merge (NODE_ID_ALIAS normaliza aliases)

**computeNRS(nodeId)**: retorna NUMBER (0-100), NO objeto. Toda la UI lo maneja como número.

**LINKS** (post-filter): objetos `{source, target, w, rel, type}` — usar `lid(l.source)` para acceder al ID.

**Quotes**: `MKT.quotes[ticker] = {close, prev, live}` — NO usar `q.c` ni `q.pc`.

## Nombres

- App: **Khipu Finance** (no NEXUS)
- Voz: **Bixby** (ElevenLabs Conversational AI, no confundir con Samsung Bixby)
- LLM: Claude vía ANTHROPIC_KEY

## Variables de entorno

```
SECRET_KEY, FINNHUB_KEY, ANTHROPIC_KEY, ELEVENLABS_KEY, ELEVENLABS_AGENT_ID,
AV_KEY, FMP_KEY, MARKETSTACK_KEY, RAG_URL, MIROFISH_URL
```

## API keys en el browser

Las keys del browser se guardan en localStorage (Keys.set/Keys.get) — NUNCA en el server ni en el código. En modo servidor (SERVER_MODE=true) las keys viven en .env del servidor.

## Funciones globales clave

- `switchTab(tab)`: tab ∈ {map, market, analysis, geo, simulation, space}
- `jumpTo(nodeId)`: selecciona nodo en el grafo
- `activateStress(nodeId)`: activa cascada de fallo
- `computeNRS(nodeId)`: → number 0-100
- `computeNodeRadius(nodeId)`: → number en px
- `renderMarket()`: re-renderiza tabla de mercado
- `window.nexusCore.runPreset(presetId)`: lanza simulación
- `window._openSecondBrain(nodeId)`: abre panel Second Brain
- `window.BixbyVoice.toggle()`: activa/desactiva Bixby

## Categorías (35)

Definidas en CATS (19) + CATS_NEW (17) merged con Object.assign(CATS, CATS_NEW).
CSS vars: `--c-{cat}` definidas en :root y .dark.

## ScenarioBuilder presets

`ScenarioBuilder.PRESETS` (objeto, no array): taiwan_conflict, china_chip_ban_total, hbm_shortage_2027, openai_ipo_impact, starshield_reveal

## Errores comunes

- `switchTab('sim')` → INCORRECTO, usar `switchTab('simulation')`
- Destruir `computeNRS` devuelve número, no `{total, color, label}`
- `LINKS_EXPAND` usa `{s,t,type}` (objetos) — el merge ya los convierte
- `getCatColorHex()` está definida en engine/graph3d.js, no disponible antes de que cargue
