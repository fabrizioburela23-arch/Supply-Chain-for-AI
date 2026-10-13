---
tipo: "modulo"
capa: "Investigación"
ruta: "research/falsifiers.py"
lenguaje: "python"
lineas: 202
aliases: ["research/falsifiers.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/falsifiers.py

> Módulo · capa [[Capa Investigación]] · 202 líneas · `research/falsifiers.py`

## Para qué sirve

falsadores ESTRUCTURADOS y verificables (C8, misión de reparación 2026-10-04).

## API pública

- clase `FalsifierRule` _(línea 29)_
- `normalize(rules)` — Lista de dicts válidos (ignora entradas rotas en vez de romper). _(línea 62)_
- `direction_errors(stance_or_decision, rules)` — Un falsador debe CONTRADECIR la postura: para una postura/decisión alcista el precio (o el exceso) tiene que CAER (op '<'); para una … _(línea 76)_
- `describe(rule, lang=…)` _(línea 92)_
- `check_rules(rules, baseline_date, series, bench=…, today=…)` — ¿Alguna regla se disparó entre la foto de partida y hoy? Devuelve {rule, date, value} de la PRIMERA que se dispara, o None. Reglas vencidas … _(línea 101)_
- `apply_falsifiers(session, now, get_series, today)` — Recorre las claims ACTIVAS con reglas y foto de partida calificable; si una regla se disparó → status 'falsified' + … _(línea 136)_

## Depende de

- [[core.decision_sites.py]] — importa `decision_sites`
- [[research.models.py]] — importa `ClaimBaseline`, `ClaimOutcome`, `ResearchClaim`

## Lo usan

- [[research.committee.py]] — lo importa
- [[research.outcomes.py]] — lo importa
- [[research.schemas.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_repair_committee.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-04 (h) — MISIÓN DE REPARACIÓN P0 INVESTIGACIÓN (R1-R6, sw v201)]]
