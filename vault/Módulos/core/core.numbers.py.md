---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/numbers.py"
lenguaje: "python"
lineas: 869
aliases: ["core/numbers.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/numbers.py

> Módulo · capa [[Capa Infraestructura]] · 869 líneas · `core/numbers.py`

## Para qué sirve

guardián de CIFRAS (anti-alucinación numérica).

## API pública

- clase `Mention` _(línea 390)_
- clase `Facts` — Valores de los DATOS, separados por tipo. Cada valor: (número, signo). _(línea 548)_
- `facts_from_text(text)` _(línea 669)_
- `evidence_numbers(evidence)` — Hechos (por tipo) del paquete de evidencia [{title, excerpt}]. _(línea 673)_
- `supported(m, facts)` — ¿La cifra `m` (Mention) está respaldada por `facts`? _(línea 757)_
- `unsupported_mentions(text, facts, kinds=…)` _(línea 786)_
- `unsupported_figures(text, facts, kinds=…)` — Cifras (texto tal como aparece) de `text` sin respaldo en `facts`. _(línea 790)_
- `unsupported_money(text, vals)` — Solo dinero/precios (contrato viejo; lo usan retract/withhold de claims guardadas). _(línea 795)_
- `money_mentions(text)` — [(texto_original, valor_en_B | None si es precio unitario, valor_crudo)] _(línea 800)_
- `check_numbers(result, evidence, kinds=…)` — Errores (lista vacía = ok) por cifras que NO están en la evidencia. _(línea 809)_
- `unsupported_in(text, source_text, kinds=…)` — Cifras de `text` que NO aparecen en `source_text` (los DATOS del mensaje). `source_text` puede ser un Facts ya construido (core/ai lo arma … _(línea 843)_
- `mark_unsupported(text, bad, kinds=…, facts=…)` — Marca en el texto cada cifra sin respaldo (no la borra: el lector ve que NO está verificada), en el TRAMO exacto de la cifra. Seguro dentro … _(línea 850)_

**Internas** (empiezan con `_`): `_last`, `_governed`, `_sub_rx`, `_hints`, `_Headers`, `_cands`, `_to_float`, `_scale_of`, `_segment_before`, `_ctx`, `_mentions`, `_no_overlap`, `_range_heads`, `_num_group`, `_strip_span`, `_tol`, `_pct_ok`, `_sign_ok`, `_close`, `_near`, `_window`

## Depende de

- [[core.governance.py]] — importa `governance`

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

_Además lo importan 6 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_analytics.py]]
- [[tests.test_block0_guardian_corpus.py]]
- [[tests.test_block0_numbers.py]]
- [[tests.test_block0_review.py]]
- [[tests.test_governance_seed_parity.py]]
- [[tests.test_research.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-12 (e) — BLOQUE 0 DE BRECHAS_V2 - CIFRAS Y PUBLICACIÓN SEGURAS]]
- [[Sesión 2026-10-02 (noche) — ANÁLISIS MÁS PROFUNDO + CONCLUSIONES EN TODAS PARTES (sw v179)]]
- [[Sesión 2026-10-02 (b) — COMITÉ CON ANÁLISIS REAL DE IA + INVESTIGACIÓN QUE NO SE CAE]]
