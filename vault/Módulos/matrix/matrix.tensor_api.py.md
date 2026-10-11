---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "matrix/tensor_api.py"
lenguaje: "python"
lineas: 105
aliases: ["matrix/tensor_api.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# matrix/tensor_api.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 105 líneas · `matrix/tensor_api.py`

## Para qué sirve

/api/tensor/\*: la ontología nivel 2 (matrix/tensor.py) por HTTP.

## API pública

- `tensor_status()` _(línea 30)_
- `tensor_node(nid)` _(línea 40)_
- `tensor_rank()` _(línea 53)_
- `tensor_suggest()` — {id} de una empresa existente, o {node:{label, cat, sector, country, role}} de una NUEVA. _(línea 67)_
- `tensor_eval()` — Calidad medida de la auto-conexión (vínculos reales ocultos). Se calcula 1 vez por snapshot. _(línea 88)_

**Internas** (empiezan con `_`): `_T`, `_err`

## Depende de

- [[core.http.py]] — importa `rate_limit`
- [[matrix.tensor.py]] — importa `tensor`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/tensor/eval` | `tensor_eval` | — |
| `GET` | `/api/tensor/node/<path:nid>` | `tensor_node` | [[engine.oswindows.js]], [[engine.xray.js]], 3 pruebas |
| `GET` | `/api/tensor/rank` | `tensor_rank` | 1 prueba |
| `GET` | `/api/tensor/status` | `tensor_status` | — |
| `POST` | `/api/tensor/suggest` | `tensor_suggest` | 1 prueba |

Grupos: [[API tensor]]

## Pruebas que lo cubren

- [[tests.test_khipus_os_windows.py]]
- [[tests.test_overnight_ui_xray_research.py]]
- [[tests.test_tensor.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (ff) — ONTOLOGÍA NIVEL 2 - TENSORES + AUTO-CONEXIÓN (sw v241)]]
