---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "core/decide_api.py"
lenguaje: "python"
lineas: 28
aliases: ["core/decide_api.py"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# core/decide_api.py

> Módulo · capa [[Capa Chat y agentes]] · 28 líneas · `core/decide_api.py`

## Para qué sirve

/api/decide/\*: estado del modo sombra de Jev (lectura, PIN de operador).

## API pública

- `status()` _(línea 13)_
- `shadow()` _(línea 23)_

## Depende de

- [[core.decide.py]] — importa `available`, `control_features`, `shadow_mode`, `shadow_report`
- [[core.http.py]] — importa `rate_limit`
- [[core.pin.py]] — importa `require_operator`

## Lo usan

- [[server.py]] — lo importa

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/decide/shadow` | `shadow` | [[engine.aispend.js]] |
| `GET` | `/api/decide/status` | `status` | [[engine.aispend.js]], 1 prueba |

Grupos: [[API decide]]

## Pruebas que lo cubren

- [[tests.test_jev_status_label.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-04 (c) — JEV (TYPESAFE) EN MODO SOMBRA - PORTERO DEL CHAT (sw v188)]]
