# Arquitectura de 4 Capas — Khipus AI Finance Intelligence

Diseño de Fabrizio (2026-07-10), estructurado por latencia, costo y
profundidad de pensamiento. Cada capa tiene su implementación REAL en el
código — esto no es un diagrama aspiracional.

## Capa 1 — Inconsciente / Refleja (milisegundos, costo cero)

El sistema ejecuta sin "pensar": tool calling reflejo y datos directos.

| Pieza | Dónde vive |
|---|---|
| Parser KHIPU (`TSMC XRAY`, `SHOCK nvidia`…) — se intenta ANTES de llamar a la IA | `engine/khipu_lang.js` |
| Client tools de Bixby (23 herramientas silenciosas registradas en ElevenLabs) | `engine/voice.js` + `_bixby_client_tools()` en `server.py` |
| Enrutador de la Cabina (regex: desármame/cae/compara/investiga…) | `engine/cockpit.js → ask()` |
| Proxies de datos (quotes, news, GDELT, satélites) | `server.py` |
| Motor de estados client-side (~7 ms/simulación, 60 fps) | `engine/statematrix.js` |

## Capa 2 — Preconsciente (contexto listo ANTES de usarse)

Lo que el usuario no ve pero ya está preparado: caché + subgrafo activo.

| Pieza | Dónde vive |
|---|---|
| Caché TTL (SimpleCache / Redis automático si hay `REDIS_URL`): canvas 30 min, IA 30 min, matrices 5 min, quotes 15 s | `server.py`, `matrix/api.py` |
| **Grafo semántico activo**: `build_context()` — el subgrafo hiper-filtrado alrededor de lo preguntado (foco + vecinos top por peso + chokepoints), compacto para no inflar el prompt | `core/semantic.py` |
| Detección barata de empresas en una pregunta (sin IA) | `core/semantic.py → extract_companies()` |
| Snapshot siempre disponible (555 empresas) aunque no haya DB | `data/grafo_v0.json` (caché de módulo) |

## Capa 3 — Consciente (el LLM, solo tokens necesarios)

`_ai_complete()` (cascada claude→gemini→nvidia en `core/ai.py`) recibe SOLO
el contexto hiper-filtrado de la Capa 2 — nunca el grafo completo. Usos:
Canvas IA (`/api/canvas/generate`), análisis (`/api/ai/analyze`), Bixby
(`/api/ai/command`), agentes de la ontología (`_ai_explain`).

## Capa 4 — Investigación Profunda (bucle agéntico, 30-90 s)

Para preguntas complejas. Bucle multi-paso en background con polling:

```
POST /api/deep/analyze {question}      ← lo dispara la Cabina ("investiga …")
                                          o Bixby por voz (tool deep_analysis)
  1. PLAN      la IA descompone la pregunta en sub-análisis
  2. REUNIR    Capa 2: build_context() → subgrafo activo de las empresas foco
  3. SIMULAR   matrices del servidor: propagate() con hiperaristas activas
  4. SINTETIZAR la IA redacta: TESIS · EVIDENCIA (números reales) · RIESGOS ·
               QUÉ VIGILAR
GET /api/deep/status                   ← pasos en vivo + resultado
```

Implementación: `_deep_run()` en `server.py` · escena `stageDeep` en
`engine/cockpit.js` · herramienta `deep_analysis` en `engine/voice.js`.

## Flujo completo de una pregunta

```
"¿qué pasa si cae TSMC?"      → Capa 1 (regex) → simulación instantánea (7 ms)
"TSMC XRAY"                   → Capa 1 (KHIPU) → X-Ray sin IA
"grafica los márgenes de …"   → Capa 3 con caché de Capa 2 (2ª vez: instantáneo)
"investiga la energía nuclear
 para datacenters"            → Capa 4 (plan→contexto→simulación→síntesis)
```

Además, la app se mantiene relevante SOLA (Etapa D): el ciclo de agentes
(`/api/ontology/agents/cycle`, hilo background cada ~10 min) corre los 5
agentes — incluido 📡 RadarEmpresas, que detecta empresas nuevas en las
noticias y las incorpora al grafo con auditoría reversible (`agent:auto`).
