# Migración del FE a React + Vite (strangler-fig)

Rama: `feature/react-vite-frontend` — **NO fusionar a main hasta que Fabrizio
lo pida.** El app clásico (`app.html` + `engine/*.js`) sigue intacto y en
producción; este directorio es el reemplazo incremental.

## Por qué strangler-fig y no big-bang

`app.html` tiene ~12.800 líneas + ~30 módulos IIFE en `engine/` + ~20 catálogos
globales en `nodes/`, todos acoplados por `window.*`. Reescribir todo de golpe
garantiza regresiones invisibles. En su lugar: un app React que crece panel a
panel, con la lógica pura extraída a módulos ES **con unit tests** (lo que el
monolito nunca tuvo), hasta que el clásico quede vacío.

## Convenciones (contrato para TODO código nuevo aquí)

1. **JavaScript + JSDoc** (no TypeScript) — coherente con el resto del repo.
2. **Nada de `window.*`** — todo import/export ES. Los globals del clásico
   (`NODES`, `LINKS`, `computeNRS`, `window.KHIPU`…) se portan a `src/lib/`.
3. **HTTP solo vía `src/api/client.js`** (`get`/`post`, ApiError, timeout).
   Las keys NUNCA llegan al browser (SERVER_MODE, igual que el clásico).
4. **Vocabulario solo vía `VocabularyContext`** (`GET /api/vocabulary`) — está
   PROHIBIDO redeclarar listas de tipos/relaciones/sectores en componentes
   (así murieron las 5 copias divergentes del clásico).
5. **Tests con Vitest** colocados junto al módulo (`foo.js` → `foo.test.js`).
   Lógica pura: tests de tabla. Componentes: @testing-library/react + jsdom,
   mockeando `fetch` (no llamadas de red reales en tests).
6. **Estados de carga SIEMPRE con icono animado** (clase `.loading`) — pedido
   explícito de Fabrizio. Errores con `.error-box`, nunca pantalla vacía.
7. **Español primero** en UI (el usuario es hispanohablante); textos en el
   componente, no hardcodeados en la lógica.
8. Datos del grafo: `src/data/grafo_v0.json` (snapshot 555 nodos/1623 links,
   incluye categorías y sectores) como fallback; el vivo llega por API.

## Estado de la migración

| Área del clásico | Destino React | Estado |
|---|---|---|
| Cabina de Bixby (cockpit.js, pantalla inicial) | `components/Cockpit.jsx` | ✅ base (chips + KHIPU + insights) |
| Grafo 2D (app.html D3) | `components/GraphView.jsx` | ✅ base (fuerzas + sectores + click) |
| Mercado (renderMarket) | `components/MarketPanel.jsx` | ✅ base (quotes vivos) |
| Noticias (5 renderers duplicados) | `components/NewsPanel.jsx` | ✅ base (UN solo renderer, fuente+enlace visibles) |
| Parser KHIPU (khipu_lang.js) | `lib/khipu.js` | ✅ portado con tests |
| NRS (computeNRS de app.html) | `lib/nrs.js` | ✅ portado con tests |
| Merge de grafo + alias (merge_graph.js) | `lib/mergeGraph.js` | ✅ portado con tests |
| Sentimiento de titulares (regex app.html) | `lib/sentiment.js` | ✅ portado con tests |
| Formateadores ($, %, B/T) | `lib/format.js` | ✅ portado con tests |
| Grafo 3D (graph3d.js, three.js) | — | ⏳ pendiente |
| Voz Bixby (voice.js, ElevenLabs) | — | ⏳ pendiente |
| Geo globo / Espacio / TKG / Guía | — | ⏳ pendiente |
| Bróker/Scalping/Cripto | — | ⏳ pendiente (cuidado: PIN + confirmaciones) |
| Canvas de datos / localcharts | — | ⏳ pendiente |
| Simulación por agentes / livesim | — | ⏳ pendiente |

## Correr en desarrollo

```bash
cd frontend
npm install
npm run dev            # proxy /api → producción (solo lectura práctica)
VITE_API_TARGET=http://localhost:5050 npm run dev   # contra Flask local
npm test               # unit tests (Vitest)
npm run build          # dist/
```

## Integración a producción (cuando se fusione)

Flask servirá `frontend/dist/` detrás de una ruta (p.ej. `/next`) durante la
convivencia, y al final reemplazará a `app.html`. El SW cache (`sw.js`) NO se
toca hasta ese momento.
