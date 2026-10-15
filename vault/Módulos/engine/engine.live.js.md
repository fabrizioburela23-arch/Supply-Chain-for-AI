---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "engine/live.js"
lenguaje: "javascript"
lineas: 138
aliases: ["engine/live.js"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# engine/live.js

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 138 líneas · `engine/live.js`

## Para qué sirve

MODO EN VIVO (Etapa D, 2026-07) La app se mantiene relevante SOLA: 1) Latido de insights: cuando llegan precios nuevos, invalida el NRS y re-dibuja los insights si la pestaña Análisis está visible. 2) Ciclo de agentes: cada 10 min dispara POST /api/ontology/agents/cycle — los 5 agentes del servidor (incl. 📡 RadarEmpresas) corren y las propuestas seguras se aplican solas (auditadas, reversibles). Sin DATABASE_URL el endpoint responde 503 y esto calla — patrón opcional. 3) Indicador ● EN VIVO en el pie + toast cuando el radar aplica cambios. KHIPUS OS (2026-10-11): el indicador lleva .kos-themed → tokens --os-\* de engine/cockpit.js (claro/oscuro); textos ES/EN que se …

## API pública (globales que define)

`window.KhipuLive`

## Depende de

- [[app.html]] — usa `_tradeFetch`
- [[engine.app_main.js]] — usa `BASE`, `LANG`, `MKT`, `_appVersion`, `_showUpdatePill`
- [[sw.js]] — lo nombra por su ruta

Se carga en [[app.html]] en la posición **93 de 100** (línea 3218), después de [[engine.cockpit.js]] y antes de [[engine.command_center.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 93)
- [[engine.voice.js]] — usa `KhipuLive`
- [[engine.xray.js]] — usa `KhipuLive`

## Endpoints que llama

- `POST /api/ontology/agents/cycle` → [[ontology.api.py]] ([[API ontology]])

## Pruebas que lo cubren

- [[tests.test_infra.py]]
- [[tests.test_no_client_engine.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-28 (c) — DOSSIER PARA TODAS LAS EMPRESAS + DATOS EN VIVO (sw v151)]]
- [[Sesión 2026-07-10 — modo máximo (feedback - perfeccionar Khipu, 555 empresas, vivo, 3D)]]
