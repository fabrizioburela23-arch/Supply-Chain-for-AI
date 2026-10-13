---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/__init__.py"
lenguaje: "python"
lineas: 13
aliases: ["core/__init__.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/__init__.py

> Módulo · capa [[Capa Infraestructura]] · 13 líneas · `core/__init__.py`

## Para qué sirve

helpers compartidos entre server.py (Flask) y ontology/ (agentes).

## API pública

_Sin funciones ni clases públicas de nivel superior._

## Depende de

_Nada interno._

## Lo usan

- [[core.screener.py]] — lo importa
- [[matrix.api.py]] — lo importa
- [[matrix.engine.py]] — lo importa
- [[ontology.db.py]] — lo importa
- [[ontology.service.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 5 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_hot_contract.py]]
- [[tests.test_hot_invalidation.py]]
- [[tests.test_hot_review_fixes.py]]
- [[tests.test_hot_views_parity.py]]
- [[tests.test_ops_graph_version.py]]
