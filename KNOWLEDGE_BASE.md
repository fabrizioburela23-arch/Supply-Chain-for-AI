# Khipus AI Finance Inteligence — Base de conocimiento

> Documento maestro del proyecto. Importable en Obsidian (arrastra este `.md` a tu vault
> o apunta Obsidian a la carpeta del repo). Actualizado por la sesión de desarrollo.

## Qué es
Terminal de inteligencia de inversión estilo Bloomberg + IA para tecnologías profundas:
semiconductores, IA, espacio, computación cuántica, energía nuclear y robótica. ~460+
empresas con grafo de cadena de suministro navegable, análisis por IA, voz (Bixby),
simulación agéntica y mapas 3D inmersivos.

## Arquitectura
- **`app.html`** (~12.500 líneas): toda la UI (D3 + Three.js + vanilla JS). Datos de nodos
  embebidos + cargados de `nodes/*.js`.
- **`server.py`** (Flask): proxy de datos (Finnhub/FMP/Marketstack/Alpaca/SEC), IA
  multi-proveedor, VaR/CVaR, JWT, `/vendor` (proxy de librerías), diagnóstico.
- **`engine/`**: graph3d.js (grafo 3D), planetarium.js (planeta satelital), geoglobe.js
  (globo geopolítico), geo_coords.js, voice.js (Bixby voz), command_center.js (Bixby texto),
  canvas-data.js, secondbrain.js, hypergraph.js.
- **`sim/`**: mirofish_client.js, scenario_builder.js.
- **`nodes/`**: nodes_expand*.js, nodes_spacex.js, nodes_nuclear.js, nodes_expand4.js,
  preipo_intel.js, links_*.js.
- **`rag/`**: microservicio ChromaDB (Second Brain) — se despliega aparte (ver SETUP.md).

## Features principales
| Feature | Dónde | Cómo funciona |
|---|---|---|
| Mapa de la cadena | tab Mapa | Grafo D3 (2D) / Three.js (3D). NRS por nodo. |
| Scatter 3D inversión | 🕸 3D | Ejes: tiempo al mercado × capitalización × riesgo. Filtros 💎. |
| Mercado en vivo | tab Mercado | Precios Finnhub (WS + REST fallback), portafolio, P&L. |
| Análisis / NRS | tab Análisis | Deep-dive por empresa, Dossier 5 años, 📄 SEC 10-K, 🧠 Second Brain. |
| Geopolítica | tab Geopolítica | Globo 3D con empresas por región + chokepoints + rutas. |
| Simulación War-Room | tab Simulación | 2 motores: 🤖 IA Simple / 🧬 MiroFish. |
| Espacio | tab Espacio | Planeta 3D con satélites reales (CelesTrak). |
| Canvas IA | tab Canvas | Gráficos/tablas generados por IA en lenguaje natural. |
| Bixby | botón header / ⌘K | Copiloto de voz+texto: ejecuta acciones + genera Canvas inline. |
| Carteras editables | detalle empresa | Botones +C1/+C2 (persistidas en localStorage). |
| Empresa privada | detalle (pre-IPO) | Rondas, inversores, timeline IPO, hitos. |

## IA (multi-proveedor con fallback)
`_ai_complete()` prueba en orden (`AI_ORDER`, default `claude,gemini,nvidia`); si uno falla,
pasa al siguiente. Todas las features de IA (Canvas, Bixby, análisis, research SEC) lo usan.
- Claude (Anthropic) — principal, requiere saldo.
- Gemini (Google, gratis) y NVIDIA NIM (gratis MVP) — respaldo.

## Variables de entorno (Railway, servicio principal)
Configuradas: ANTHROPIC_KEY, GEMINI_KEY, ELEVENLABS_KEY, ELEVENLABS_AGENT_ID,
ELEVENLABS_ALLOW_OVERRIDE, FINNHUB_KEY, FMP_KEY, MARKETSTACK_KEY, AV_KEY, ALPACA_KEY,
ALPACA_SECRET, ALPACA_BASE, AI_MODEL, MIROFISH_URL.
Recomendadas: SECRET_KEY (fuerte), AI_ORDER, RAG_URL (tras desplegar el RAG).
Opcionales: NVIDIA_KEY, MIROFISH_TOKEN, SEC_USER_AGENT.

## Endpoints clave (server.py)
- `/api/health`, `/api/diagnostics` (🩺 estado en vivo de cada servicio).
- `/api/quote`, `/api/quotes`, `/api/candles` (precios).
- `/api/ai/command` (Bixby texto), `/api/canvas/generate` (Canvas IA).
- `/api/company/research/<ticker>` (síntesis 10-K SEC), `/api/dossier/<ticker>`.
- `/api/space/tle` (satélites), `/api/mirofish/*`, `/api/rag/*`.
- `/vendor/<asset>` (proxy de d3/three/chart/satellite + texturas, para redes que bloquean CDNs).

## "Funciona en cualquier computadora"
Las librerías y texturas se sirven desde el propio servidor (`/vendor`) para no depender de
CDNs externos que algunas redes bloquean. El service worker es network-first (siempre la
última versión). Si en un equipo se ve viejo/roto → abrir en incógnito (evita caché vieja).

## Limitaciones / pendientes conocidos
- RAG / Second Brain: requiere desplegar `rag/` como 2º servicio en Railway (ver SETUP.md).
- Voz Bixby: el timeout de inactividad se ajusta en el panel de ElevenLabs.
- Trading real requiere cuenta Alpaca; si falla, cae a operación simulada (paper).

## Docs relacionados
- `SETUP.md` — pasos de configuración (env vars, RAG, ElevenLabs, verificación).
- `CLAUDE.md` — convenciones internas del código.
