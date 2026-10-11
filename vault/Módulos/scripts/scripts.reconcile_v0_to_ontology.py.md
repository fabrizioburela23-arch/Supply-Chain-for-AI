---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "scripts/reconcile_v0_to_ontology.py"
lenguaje: "python"
lineas: 101
aliases: ["scripts/reconcile_v0_to_ontology.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# scripts/reconcile_v0_to_ontology.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 101 líneas · `scripts/reconcile_v0_to_ontology.py`

## Para qué sirve

G3: reconciliar el catálogo (data/grafo_v0.json) con la ontología en Postgres SIN borrar nada.

## API pública

- `main(argv=…)` _(línea 33)_

## Depende de

- [[ontology.db.py]] — importa `session_scope`
- [[ontology.reconcile.py]] — importa `reconcile`

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Variables de entorno que lee (solo nombres)

- [[ENV DATABASE_URL]]

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
