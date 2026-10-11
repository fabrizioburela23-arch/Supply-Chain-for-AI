---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/country_geo.py"
lenguaje: "python"
lineas: 222
aliases: ["core/country_geo.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/country_geo.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 222 líneas · `core/country_geo.py`

## Para qué sirve

coordenadas de referencia por PAÍS (la capital), para capas que solo dicen "qué país" (avisos de viaje del Departamento de Estado, cortes de internet). Nombre en inglés normalizado → (lat, lon, nombre_es). Se marca precisión 'country' en la UI: es un punto de referencia, no el lugar exacto.

## API pública

- `lookup(name)` — Nombre de país (inglés) → {lat, lon, es, en} o None. _(línea 213)_

**Internas** (empiezan con `_`): `_norm`

## Depende de

_Nada interno._

## Lo usan

- [[core.world_feeds.py]] — lo importa

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-05 (p) — GEOPOLÍTICA - CAPAS EN PAUSA REVIVIDAS + RIESGO PAÍS + CORTES]]
