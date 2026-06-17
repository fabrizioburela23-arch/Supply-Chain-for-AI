# Khipu Finance 🌐

**Bloomberg Terminal + Jarvis de IA** para la cadena de valor global de semiconductores, IA y espacio.

> 450+ empresas · 900+ conexiones · 35 categorías · NRS Risk Score · Bixby AI Voice · 3D Graph · RAG Second Brain

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | HTML/CSS/JS vanilla · D3.js v7 · Three.js r128 · Chart.js 4 |
| Backend | Flask 3 · Python 3.11 · Gunicorn |
| AI / Voz | Claude (Anthropic) · ElevenLabs Conversational AI (Bixby) |
| RAG | ChromaDB · Flask microservice (puerto 5051) |
| Simulación | MiroFish (multi-agent) · LiteLLM proxy → Claude |
| Infra | Docker Compose · Redis · Service Worker (PWA) |

## Deploy en Railway (recomendado para producción)

Railway despliega los 3 servicios desde el mismo repositorio.

### Paso 1 — Crear el proyecto
En [railway.app](https://railway.app) → **New Project → Deploy from GitHub repo** → selecciona `supply-chain-for-ai`.

### Paso 2 — Crear los 3 servicios

| Servicio | Root Directory | Descripción |
|----------|---------------|-------------|
| **khipu** | `/` (raíz) | App principal Flask |
| **rag** | `rag/` | ChromaDB Second Brain |
| **litellm** | `litellm/` | Proxy OpenAI → Claude |

Para cada servicio adicional (rag, litellm): en el proyecto Railway → **+ New Service → GitHub Repo** → mismo repo → cambia el **Root Directory** al subdirectorio correspondiente.

### Paso 3 — Variables de entorno

**Servicio `khipu`** (app principal):
```
SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
ANTHROPIC_KEY=sk-ant-...
FINNHUB_KEY=...
FMP_KEY=...
MARKETSTACK_KEY=...
AV_KEY=...
RAG_URL=${{rag.RAILWAY_PRIVATE_DOMAIN}}
MIROFISH_URL=${{litellm.RAILWAY_PRIVATE_DOMAIN}}
LITELLM_MASTER_KEY=khipu-litellm-key
```

**Servicio `rag`**:
```
ANTHROPIC_KEY=sk-ant-...
CHROMA_PATH=/data/chroma
```
> Añade un **Volume** en Railway montado en `/data/chroma` para persistir la base vectorial.

**Servicio `litellm`**:
```
ANTHROPIC_API_KEY=sk-ant-...
LITELLM_MASTER_KEY=khipu-litellm-key
```

### Paso 4 — Variables de referencia entre servicios
En Railway, las variables `${{rag.RAILWAY_PRIVATE_DOMAIN}}` y `${{litellm.RAILWAY_PRIVATE_DOMAIN}}` se resuelven automáticamente con el hostname interno de cada servicio. Railway conecta los servicios en red privada sin exponerlos al público.

### Paso 5 — Deploy
Railway detecta los `railway.toml` en cada directorio y despliega automáticamente. La app principal queda accesible en `https://tu-proyecto.railway.app`.

---

## Inicio rápido local

### Con Docker Compose
```bash
cp .env.example .env
# Edita .env con tus API keys
docker-compose up -d
# Abre http://localhost:5000
```

### Solo servidor Python
```bash
pip install -r requirements.txt
cp .env.example .env && nano .env
python server.py
```

### Sin servidor (modo standalone)
Abre `app.html` directamente en el navegador. Configura las API keys en ⚙ Configuración.

## Variables de entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `SECRET_KEY` | ✅ | Clave JWT para la API v1 |
| `FINNHUB_KEY` | ✅ | Precios en tiempo real (free tier OK) |
| `ANTHROPIC_KEY` | ✅ | Claude para análisis IA y Bixby |
| `ELEVENLABS_KEY` | Bixby | ElevenLabs Conversational AI |
| `ELEVENLABS_AGENT_ID` | Bixby | ID del agente Bixby en ElevenLabs |
| `AV_KEY` | VaR/CVaR | Alpha Vantage (free tier) |
| `FMP_KEY` | Opciones | Financial Modeling Prep |
| `MARKETSTACK_KEY` | Opciones | Marketstack EOD |
| `RAG_URL` | Docker | URL del microservicio RAG (auto en Docker) |
| `MIROFISH_URL` | Simulación | URL de MiroFish / LiteLLM proxy |

## Arquitectura

```
Browser (app.html)
├── D3.js force graph (2D) — 450+ nodos
├── Three.js 3D graph (toggle con botón 3D)
├── TemporalHypergraph — hiperedges de eventos
├── SecondBrain panel — 5 capas RAG
├── BixbyVoice — ElevenLabs WebSocket
└── MiroFishClient — simulaciones multi-agente

Flask server (server.py :5000)
├── /api/* — proxies de Finnhub, FMP, GDELT, Space, Claude
├── /v1/* — API pública con JWT auth (tiers)
└── /api/rag/* — proxy al microservicio RAG

RAG server (rag/rag_server.py :5051)
└── ChromaDB — 5 colecciones vectoriales

LiteLLM proxy (:4000)
└── OpenAI SDK → Claude (para MiroFish)
```

## Funcionalidades principales

- **Grafo 2D/3D**: 450+ empresas con zoom, filtros, stress-test cascada, pathfinder
- **NRS Risk Score**: Puntuación 0-100 compuesta (geo + cadena + mercado + fundamental + concentración)
- **Bixby**: Asistente de voz IA — navega el grafo, ejecuta stress-tests, consulta Second Brain por voz
- **Second Brain**: Panel RAG con 5 capas (mercado, noticias, tesis, simulación, red)
- **VaR/CVaR**: Cálculo de riesgo de portfolio con datos históricos Alpha Vantage
- **Simulaciones**: 5 presets geopolíticos via MiroFish multi-agent
- **GDELT News**: Búsqueda de noticias globales en tiempo real con auto-hiperedges en 3D
- **Alertas de precio**: Notificaciones del sistema cuando un ticker cruza un umbral
- **API pública v1**: JWT auth por tiers (free/starter/pro/business/enterprise)

## Nodos incluidos

| Categoría | Ejemplos |
|-----------|---------|
| Foundry / IDM | TSMC, Samsung, Intel, GlobalFoundries |
| Fabless | Nvidia, AMD, Qualcomm, Broadcom, Apple Silicon |
| Equipamiento | ASML, Applied Materials, Lam Research, KLA |
| Cloud / NeoClouds | AWS, Azure, Google Cloud, CoreWeave, Lambda Labs |
| AI Labs | OpenAI, Anthropic, DeepMind, xAI, Mistral |
| Espacio | SpaceX, Rocket Lab, Planet Labs, AST SpaceMobile |
| AI Defense | Anduril, Shield AI, Palantir, L3Harris |
| Memoría | SK Hynix, Micron, Samsung Memory |
| Quantum | IBM Quantum, IonQ, Rigetti, D-Wave |

## Licencia

Datos compilados de fuentes públicas y estimaciones de analistas (jun. 2026).
