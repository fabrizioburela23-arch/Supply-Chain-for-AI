---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "matrix/tensor_api.py"
lenguaje: "python"
lineas: 115
aliases: ["matrix/tensor_api.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# matrix/tensor_api.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 115 líneas · `matrix/tensor_api.py`

## Para qué sirve

/api/tensor/\*: la ontología nivel 2 (matrix/tensor.py) por HTTP.

## API pública

- `tensor_status()` _(línea 29)_
- `tensor_node(nid)` _(línea 39)_
- `tensor_rank()` _(línea 61)_
- `tensor_suggest()` — {id} de una empresa existente, o {node:{label, cat, sector, country, role}} de una NUEVA. _(línea 75)_
- `tensor_eval()` — Calidad medida de la auto-conexión (vínculos reales ocultos). Se calcula 1 vez por GENERACIÓN del grafo (antes leía la fecha de T.SNAPSHOT, … _(línea 96)_

**Internas** (empiezan con `_`): `_T`, `_err`

## Depende de

- [[core.__init__.py]] — importa `card`, `hot`
- [[core.http.py]] — importa `rate_limit`
- [[matrix.tensor.py]] — importa `tensor`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/tensor/eval` | `tensor_eval` | 1 prueba |
| `GET` | `/api/tensor/node/<path:nid>` | `tensor_node` | [[engine.oswindows.js]], [[engine.xray.js]], 3 pruebas |
| `GET` | `/api/tensor/rank` | `tensor_rank` | 1 prueba |
| `GET` | `/api/tensor/status` | `tensor_status` | 1 prueba |
| `POST` | `/api/tensor/suggest` | `tensor_suggest` | 1 prueba |

Grupos: [[API tensor]]

## Pruebas que lo cubren

- [[tests.test_khipus_os_windows.py]]
- [[tests.test_overnight_ui_xray_research.py]]
- [[tests.test_scale_tensor.py]]
- [[tests.test_tensor.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (ff) — ONTOLOGÍA NIVEL 2 - TENSORES + AUTO-CONEXIÓN (sw v241)]]
