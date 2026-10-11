---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/tour.py"
lenguaje: "python"
lineas: 39
aliases: ["core/tour.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/tour.py

> Módulo · capa [[Capa Infraestructura]] · 39 líneas · `core/tour.py`

## Para qué sirve

el guion del recorrido de un minuto, lado Python (voz para Khipus OS, 2026-10-11).

## API pública

- `line(step, lang)` — Frase del paso `step` (0…N-1) en `lang` ('es'|'en'); None si no existe. _(línea 30)_
- `text_hash(text)` — Huella corta de una frase: entra en la clave de la caché de audio (si el guion cambia, el audio también). _(línea 37)_

**Internas** (empiezan con `_`): `_load`

## Depende de

_Nada interno._

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_voice_tour.py]]
