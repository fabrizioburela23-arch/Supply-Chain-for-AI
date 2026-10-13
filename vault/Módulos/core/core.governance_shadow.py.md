---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/governance_shadow.py"
lenguaje: "python"
lineas: 179
aliases: ["core/governance_shadow.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/governance_shadow.py

> Módulo · capa [[Capa Infraestructura]] · 179 líneas · `core/governance_shadow.py`

## Para qué sirve

FORMAS PROPUESTAS EN SOMBRA junto a las vigentes (docs/INFRA_OPERATIVA.md §5.3; paso 25).

## API pública

- `arm(force=…)` — (Re)carga la candidata si cambió el release o las propuestas. Barato; lo llama el reloj de gobernanza. _(línea 42)_
- `tap(gate, triples, raw)` — Gancho de core/gates.evaluate: encola (gate, foco, resultado vigente) si hay candidata. O(1). _(línea 83)_
- `drain(max_items=…)` — Procesa la cola en ESTE hilo (lo usa el hilo de fondo y las pruebas). Devuelve cuántos procesó. _(línea 127)_
- `stats(semver=…)` _(línea 158)_
- `state()` _(línea 170)_
- `reset_for_tests()` _(línea 175)_

**Internas** (empiezan con `_`): `_candidate`, `_empty`, `_vkey`, `_process`, `_ensure_worker`

## Depende de

- [[core.__init__.py]] — importa `engine`
- [[core.governance.py]] — importa `governance`

## Lo usan

- [[core.governance.py]] — lo importa
- [[core.governance_flow.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_governance_flow.py]]
