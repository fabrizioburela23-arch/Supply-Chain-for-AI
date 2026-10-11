---
tipo: "documento"
capa: "Documentación"
ruta: "docs/MODEL_ROUTING.md"
lenguaje: "markdown"
lineas: 24
aliases: ["docs/MODEL_ROUTING.md"]
tags: ["capa/documentacion", "tipo/documento"]
---

# docs/MODEL_ROUTING.md

> Documento · capa [[Capa Documentación]] · 24 líneas · `docs/MODEL_ROUTING.md`

## De qué trata

MODEL ROUTING — sin acoplarse a un proveedor — `research/llm.py`: `LLMProvider {generate, structured_generate, tool_call}`; `CoreProvider` envuelve UN proveedor de `core/ai.py` (claude|gemini|nvidia); `RoutedProvider` hace la cascada por agente; `FakeProvider` para tests.

## Menciona

- [[core.ai.py]]
- [[research.llm.py]]
