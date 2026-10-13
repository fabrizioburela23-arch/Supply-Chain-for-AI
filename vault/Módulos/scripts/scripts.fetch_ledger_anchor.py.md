---
tipo: "modulo"
capa: "Infraestructura"
ruta: "scripts/fetch_ledger_anchor.py"
lenguaje: "python"
lineas: 98
aliases: ["scripts/fetch_ledger_anchor.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# scripts/fetch_ledger_anchor.py

> Módulo · capa [[Capa Infraestructura]] · 98 líneas · `scripts/fetch_ledger_anchor.py`

## Para qué sirve

baja el ANCLA DIARIA pública del libro de decisiones y la guarda fuera de la base (docs/INFRA_OPERATIVA.md §2.8, paso 7, decisión D7). La corre el GitHub Action smoke-mcp.yml.

## API pública

- `fetch(url, retries=…, wait_s=…, timeout=…)` _(línea 27)_
- `validate(d)` — Lista de problemas de forma (vacía = válida). _(línea 45)_
- `main(argv=…)` _(línea 62)_

## Depende de

_Nada interno._

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

_Además lo importan 1 pruebas (lista abajo)._

## Endpoints que llama

- `GET /api/ledger/anchor` → [[core.ledger_api.py]] ([[API ledger]])

## Variables de entorno que lee (solo nombres)

- [[ENV GITHUB_OUTPUT]]
- [[ENV GITHUB_STEP_SUMMARY]]
- [[ENV KHIPU_URL]]

## Pruebas que lo cubren

- [[tests.test_ledger_anchor.py]]
