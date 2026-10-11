---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/numbers.py"
lenguaje: "python"
lineas: 172
aliases: ["core/numbers.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/numbers.py

> Módulo · capa [[Capa Infraestructura]] · 172 líneas · `core/numbers.py`

## Para qué sirve

guardián de CIFRAS (anti-alucinación numérica).

## API pública

- `money_mentions(text)` — [(texto_original, valor_en_B | None si es cifra suelta tipo precio, valor_crudo)] _(línea 63)_
- `evidence_numbers(evidence)` — Todos los valores numéricos del paquete: crudos y normalizados a B. _(línea 84)_
- `unsupported_money(text, vals)` _(línea 121)_
- `check_numbers(result, evidence)` — Errores (lista vacía = ok) por cifras que NO están en la evidencia. _(línea 125)_
- `unsupported_in(text, source_text)` — Cifras de dinero de `text` que NO aparecen en `source_text` (el input). _(línea 157)_
- `mark_unsupported(text, bad)` — Marca en el texto cada cifra sin respaldo (no la borra: el lector ve que NO está verificada). Seguro dentro de strings JSON. _(línea 163)_

**Internas** (empiezan con `_`): `_to_float`, `_mult`, `_close`, `_supported`

## Depende de

_Nada interno._

## Lo usan

- [[core.ai.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[research.agents.base.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[research.confidence.py]] — lo importa
- [[research.debate.py]] — lo importa
- [[research.runner.py]] — lo importa
- herramienta MCP `get_claim_evidence` → [[API herramientas MCP]]
- herramienta MCP `get_research` → [[API herramientas MCP]]

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_analytics.py]]
- [[tests.test_research.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-02 (noche) — ANÁLISIS MÁS PROFUNDO + CONCLUSIONES EN TODAS PARTES (sw v179)]]
- [[Sesión 2026-10-02 (b) — COMITÉ CON ANÁLISIS REAL DE IA + INVESTIGACIÓN QUE NO SE CAE]]
