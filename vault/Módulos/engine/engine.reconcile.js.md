---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "engine/reconcile.js"
lenguaje: "javascript"
lineas: 253
aliases: ["engine/reconcile.js"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# engine/reconcile.js

> Módulo · capa [[Capa Ontología y grafo temporal]] · 253 líneas · `engine/reconcile.js`

## Para qué sirve

G3 (misión de reparación 2026-10-04) 🩺 Diagnóstico → "Grafo: base vs catálogo". Muestra el dry-run de ontology/reconcile.py (GET /api/ontology/reconcile/plan), abre la lista completa (HTML) y, con el PIN de operador, aplica las categorías marcadas o deshace la última corrida. TODO por eventos: nada se borra. API: window.KhipuReconcile.mount(containerId)

## API pública (globales que define)

`window.KhipuReconcile`

## Depende de

- [[app.html]] — usa `BASE`, `LANG`, `_tradeFetch`
- [[engine.explain.js]] — usa `explainChip`, `explainRegister`
- [[engine.toast.js]] — usa `KhipuToast`

Se carga en [[app.html]] en la posición **77 de 93** (línea 7916), después de [[engine.explain.js]] y antes de [[nodes.crypto_intel.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 77)
- [[app.html]] — usa `KhipuReconcile`

## Endpoints que llama

- `GET /api/ontology/reconcile/plan` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/reconcile/apply` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/reconcile/rollback` → [[ontology.api.py]] ([[API ontology]])

## Pruebas que lo cubren

- [[tests.test_overnight_ui_small_panels.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
