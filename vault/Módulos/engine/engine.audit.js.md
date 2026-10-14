---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/audit.js"
lenguaje: "javascript"
lineas: 297
aliases: ["engine/audit.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/audit.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 297 líneas · `engine/audit.js`

## Para qué sirve

🩺 Sistema → 📋 Registro → ⚖ Auditoría (INFRA_OPERATIVA paso 24, §5.6). Lista las decisiones recientes del LIBRO (filtros: tipo, quién, fecha) y por cada una: «¿Por qué?» → GET /api/ledger/why/&lt;id>: entradas, versiones de las reglas, evidencia, puertas y resultado, en lenguaje simple ES/EN (los textos los arma el servidor: core/replay.why); «Repetir» → POST /api/ledger/replay/&lt;id>: la repite con lo que el sistema sabía ENTONCES y muestra el veredicto (idéntica / distinta / no repetible y por qué). Sin PIN: el resumen (sin valores de clientes); con el PIN guardado (o «Ver detalle con PIN»): campo a campo. Sin diálogos nativos del navegador (el PIN lo pide window._tradeFetch …

## API pública (globales que define)

`window.KhipuAudit`

## Depende de

- [[app.html]] — usa `_tradeFetch`, `_tradePinStored`
- [[engine.app_main.js]] — usa `BASE`, `LANG`
- [[engine.explain.js]] — usa `explainChip`

Se carga en [[app.html]] en la posición **80 de 98** (línea 3137), después de [[engine.governance.js]] y antes de [[engine.pricehist.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 80)
- [[engine.app_main.js]] — usa `KhipuAudit`

## Endpoints que llama

- `GET /api/ledger/audit` → [[core.ledger_api.py]] ([[API ledger]])
- `GET /api/ledger/why/<decision_id>` → [[core.ledger_api.py]] ([[API ledger]])
- `GET,POST /api/ledger/replay/<decision_id>` → [[core.ledger_api.py]] ([[API ledger]])

## Pruebas que lo cubren

- [[tests.test_cierre_defectos.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (h) — PASO 24 - REPETIR DECISIONES (replay), IMPLEMENTACIONES RETENIDAS]]
