---
tipo: "modulo"
capa: "Comité"
ruta: "research/debate.py"
lenguaje: "python"
lineas: 385
aliases: ["research/debate.py"]
tags: ["capa/comite", "tipo/modulo"]
---

# research/debate.py

> Módulo · capa [[Capa Comité]] · 385 líneas · `research/debate.py`

## Para qué sirve

DEBATE CON IA del comité (cada puesto razona de verdad).

## API pública

- clase `SeatStatement` _(línea 56)_
- clase `Rebuttal` _(línea 70)_
- `seat_package(seat, label, symbol, conv, claims_by_id, cref, evidence_rows, others, live_line, risk_line)` — Texto que recibe UN puesto. evidence_rows: {claim_id: [ {title, excerpt, date, type} ]}. _(línea 126)_
- `run_statements(seats, label, symbol, conv, claims_by_id, cref, evidence_rows, live_line, risk_line, provider_factory, on_result=…)` — Ronda 1 en paralelo. on_result(seat, obj|None, meta|err) se llama en el hilo del comité a medida que termina cada puesto (para publicar EN … _(línea 211)_
- `pick_pairs(statements, max_n=…)` — Cruces (quien_responde, a_quien) entre posturas opuestas: primero la minoría responde a la mayoría (su argumento más convencido) y luego la … _(línea 261)_
- `run_rebuttals(pairs, statements, seats_by_id, label, provider_factory, on_result=…)` _(línea 283)_
- `statement_msg(seat, obj, meta, source=…)` _(línea 325)_
- `rebuttal_msg(seat, opp_seat, obj, meta)` _(línea 348)_
- `debate_lines(statements, rebuttals, seats_by_id)` — Resumen del debate para el paquete del Presidente (S# = intervenciones). _(línea 365)_

**Internas** (empiezan con `_`): `_concurrency`, `_cfg_int`, `_seat_schema`, `_reb_schema`, `_valid_refs`, `_numbers_errs`, `_check_seat`, `_check_reb`, `_call`

## Depende de

- [[core.ai_usage.py]] — importa `bind`
- [[core.numbers.py]] — importa `evidence_numbers`, `unsupported_money`
- [[research.deliberation.py]] — importa `_msg`
- [[research.llm.py]] — importa `estimate_cost`
- [[research.runner.py]] — importa `_bg_slots`, `agent_parallelism`

## Lo usan

- [[research.committee.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV COMMITTEE_MAX_SEATS]]

## Pruebas que lo cubren

- [[tests.test_repair_research.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-02 (b) — COMITÉ CON ANÁLISIS REAL DE IA + INVESTIGACIÓN QUE NO SE CAE]]
