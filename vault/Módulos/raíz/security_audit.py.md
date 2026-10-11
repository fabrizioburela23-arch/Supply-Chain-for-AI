---
tipo: "modulo"
capa: "Infraestructura"
ruta: "security_audit.py"
lenguaje: "python"
lineas: 182
aliases: ["security_audit.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# security_audit.py

> Módulo · capa [[Capa Infraestructura]] · 182 líneas · `security_audit.py`

## Para qué sirve

Khipu Finance (Fase 2H)

## API pública

- `green(s)` _(línea 31)_
- `red(s)` _(línea 32)_
- `yellow(s)` _(línea 33)_
- `bold(s)` _(línea 34)_
- `check(ok, name, detail=…)` _(línea 37)_
- `scan_secrets()` _(línea 62)_
- `main()` _(línea 86)_

**Internas** (empiezan con `_`): `_c`

## Depende de

- [[server.py]] — importa `server`
- [[server.py]] — lo nombra por su ruta

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Endpoints que llama

- `POST /v1/auth/key` → [[server.py]] ([[API v1 (pública)]])

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
