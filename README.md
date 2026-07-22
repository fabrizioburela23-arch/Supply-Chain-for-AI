# Bixby Finance 🌐

**Terminal financiera inteligente para la cadena de suministro de la IA** — estilo Bloomberg sobre un grafo de conocimiento vivo estilo Palantir, con un analista de IA (Bixby) que habla, simula, opera (simulado) y propone.

> **555 empresas · 1.623 conexiones tipadas · 9 macro-sectores · 43 categorías** — semiconductores, cloud & IA, energía/nuclear, espacio, defensa, robótica.

**Demo en vivo:** https://supply-chain-for-ai-production.up.railway.app
*(al abrir, prueba el chip "▶ Demo guiada": Bixby maneja la app solo y la narra)*

---

## Qué hace

- **Bixby (Cabina)** — pantalla inicial full-screen: chat + voz (ElevenLabs) con ~30 herramientas; abre pantallas, corre simulaciones y narra resultados. Lenguaje de comandos **KHIPU** (`NVDA SIM`, `PORT VAR`, `GRAPH ASOF 2024-01-01`) para respuestas instantáneas sin IA. **Modo demostración guiada** para pitches.
- **Simulación de shocks** — "¿qué pasa si cae TSMC?": propagación del daño por el grafo (kernel de matrices estilo DebtRank en el servidor), war-room con presets geopolíticos, y **simulación multi-agente** donde varios analistas IA debaten un escenario.
- **Hipergrafo agéntico** — los eventos sistémicos (sanciones, escaseces, conflictos) son **Factores** que amplifican la propagación; un agente los **teje solo desde las noticias** (auditado y reversible) y el panel 💡 corre la simulación en vivo y la narra con IA.
- **X-Ray de empresa** — dossier interactivo: dependencias, dependientes, **NRS Risk Score** (0-100, explicable término a término), financieros con el gráfico correcto por métrica, noticias con sentimiento.
- **◈ Grafo Temporal (bitemporal)** — viaje en el tiempo real: el grafo como era en cualquier fecha; time-travel también en la API (`?as_of=`).
- **Mercado y ejecución** — cotizaciones en vivo, **bróker simulado** (Alpaca paper, confirmación obligatoria + PIN, badge 🧪 SIMULADO), scalping 1-clic, **Top 50 cripto** con fichas bilingües, portafolios, alertas (precio/NRS/noticias por región), VaR/CVaR.
- **Mapas** — grafo 2D de fuerzas, universo 3D, globo geopolítico, planetario con satélites reales (CelesTrak), 9 matrices de relación.
- **Agentes autónomos** — radar de noticias (propone empresas nuevas), tejedor de hiperaristas, lector GDELT, evaluador de alertas y brief matinal; todo pasa por una **cola de propuestas auditada** (solo lo reversible marcado como seguro se auto-aplica).
- **API pública `/v1`** — monetizada por tiers con JWT (grafo, riesgo y simulación como servicio).

## Arquitectura

```
Browser (app.html, PWA offline-first)          frontend/ (React 19 + Vite — migración
├── D3 grafo 2D · Three.js 3D · geo/espacio     en curso, rama feature/react-vite-frontend,
├── Cabina de Bixby (cockpit) + voz             185 tests Vitest; ver frontend/MIGRATION.md)
├── Grafo Temporal bitemporal (cliente)
└── engine/*.js (~30 módulos)

Flask + gunicorn (server.py, :5050 local / Railway)
├── /api/* (62 endpoints) — proxies de mercado/noticias/IA (las keys NUNCA llegan al browser)
├── /api/ontology/* — ontología bitemporal en Postgres: eventos INMUTABLES
│   (valid_from/valid_to + recorded_at), objetos/links materializados,
│   catálogo de Acciones auditadas (Pydantic) y agentes con propuestas
├── /api/matrix/* — motor de matrices NumPy/SciPy: propagación de shocks,
│   PageRank (+ personalizado por portafolio), radio espectral ρ(T),
│   Monte Carlo opcional; modo DENSO y DISPERSO con endpoint de paridad
│   (benchmark: 50.000 nodos en ~1,2 s)
├── /api/vocabulary — registro ÚNICO de sectores/tipos/relaciones (dato, no código)
└── /v1/* — API pública monetizada (JWT por tiers) — NO usar para features internas

Postgres (Railway)  = fuente única de verdad (ontología bitemporal)
Neo4j Aura (opc.)   = espejo visual del Grafo Temporal
IA: Claude (Sonnet razonamiento / Haiku narración) con cascada Gemini/NVIDIA
    y fallback de plantilla — ningún panel sale vacío si un modelo falla
```

Ambas bases son **opcionales**: sin sus variables de entorno el servidor arranca igual (patrón try/except en todo).

## Correr localmente

```bash
pip install -r requirements.txt
cp .env.example .env        # edita tus keys (todas opcionales para arrancar)
python server.py            # http://localhost:5050
```

Frontend React (en migración, opcional):

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173 (proxy /api a producción)
VITE_API_TARGET=http://localhost:5050 npm run dev   # contra tu Flask local
```

### Deploy en Railway

**New Project → Deploy from GitHub repo** — Railway detecta `railway.toml` y despliega. Push a `main` = deploy automático (~2 min). Añade el plugin de **Postgres** para activar la ontología (inyecta `DATABASE_URL` solo).

## Variables de entorno

| Variable | Para qué | Notas |
|----------|----------|-------|
| `SECRET_KEY` | JWT de la API `/v1` | requerida en producción |
| `ANTHROPIC_KEY` | Claude (análisis, agentes, narración) | recomendada |
| `FINNHUB_KEY` | precios y noticias | free tier OK |
| `ELEVENLABS_KEY` + `ELEVENLABS_AGENT_ID` | voz de Bixby | opcional |
| `DATABASE_URL` | ontología bitemporal (Postgres) | opcional; Railway la inyecta |
| `NEO4J_URI/USER/PASSWORD` | espejo del Grafo Temporal | opcional |
| `ALPACA_KEY/SECRET/BASE` | bróker simulado (paper) | opcional |
| `GEMINI_KEY`, `NVIDIA_KEY`, `AI_ORDER` | cascada multi-IA | opcional |
| `AV_KEY`, `FMP_KEY`, `MARKETSTACK_KEY` | datos financieros extra | opcional |
| `MATRIX_ENGINE` | `dense` (default) / `sparse` | corte seguro vía `/api/matrix/parity` |
| `IMPORT_BULK_WEIGHT_FACTOR` | peso de datos importados en bulto | default 0.5 |

Las keys viven **solo en el servidor** (SERVER_MODE): el navegador nunca las ve.

## Tests

```bash
pytest tests/ -q            # backend (~100 tests; los de ontología requieren DATABASE_URL)
cd frontend && npm test     # frontend React (185 tests, Vitest)
```

Incluye tests de **equivalencia denso↔disperso** del motor de matrices, invariantes matemáticos (acotación, simetría, decaimiento), registro de vocabulario (paridad histórica exacta) e ingesta masiva (idempotencia + cuarentena).

## Estructura del repo

```
app.html          UI clásica completa (en migración a frontend/)
engine/           ~30 módulos JS (cockpit, voz, grafos, KHIPU, demo…)
nodes/            catálogo de empresas, links y hechos temporales
ontology/         ontología bitemporal + acciones auditadas + agentes + vocabulario
matrix/           motor de matrices (denso/disperso) + API
core/             cascada de IA, HTTP saneado, quotes, config
frontend/         React + Vite (strangler-fig; ver frontend/MIGRATION.md)
tests/            pytest (backend) — el FE tiene los suyos en frontend/src/
docs/ESTADO.md    memoria entre sesiones (leer primero al retomar)
data/grafo_v0.json  snapshot del grafo (555 nodos / 1.623 links)
```

## Estado y roadmap

**Hecho:** todo lo de arriba, desplegado y en demo ante inversionistas.
**En curso:** migración del FE a React (rama `feature/react-vite-frontend`), noticias con procedencia completa + filtro de objetividad (estilo Ground News financiero), escala del grafo a 12k-50k nodos (la infraestructura matemática ya lo soporta), superciclos como factores de larga duración, SaaS multi-usuario.

## Notas

- **Análisis, no asesoría financiera.** Todo el trading es sobre cuentas **simuladas** (paper), con confirmación humana obligatoria.
- Datos compilados de fuentes públicas y estimaciones de analistas (2026).
