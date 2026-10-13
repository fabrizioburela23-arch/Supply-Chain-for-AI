---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/celestrak.py"
lenguaje: "python"
lineas: 255
aliases: ["core/celestrak.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/celestrak.py

> Módulo · capa [[Capa Infraestructura]] · 255 líneas · `core/celestrak.py`

## Para qué sirve

satélites reales (CelesTrak) para el Space Monitor y el texto de Khipu.

## API pública

- `reset()` — Solo tests. _(línea 80)_
- `parse_tle_text(txt)` — Parsea formato TLE de 3 líneas → [{name,l1,l2}]. _(línea 86)_
- `refresh(now=…)` — Una ronda educada de descarga (solo los grupos que lo necesitan). Nunca lanza. _(línea 110)_
- `payload(now=…)` — Respuesta de /api/space/tle: {constellations, sats, total_real, rendered, source, …}. _(línea 189)_
- `counts(now=…)` — {label: count} de los grupos con copia REAL (para el texto de Khipu). Sin descarga extra. _(línea 225)_
- `fallback_tle()` — Órbitas de REFERENCIA cuando CelesTrak no es alcanzable (source='fallback'; la UI dice «ref»). _(línea 232)_

**Internas** (empiezan con `_`): `_now`, `_iso`, `_not_updated`, `_pause`, `_usable`

## Depende de

_Nada interno._

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_live_caps.py]]
- [[tests.test_space_satellites.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (j) — ESPACIO - VUELVEN LOS SATÉLITES (arreglo urgente) — sw v265]]
