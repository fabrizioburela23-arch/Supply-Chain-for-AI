---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/impls.py"
lenguaje: "python"
lineas: 334
aliases: ["core/impls.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/impls.py

> Módulo · capa [[Capa Infraestructura]] · 334 líneas · `core/impls.py`

## Para qué sirve

IMPLEMENTACIONES RETENIDAS (docs/INFRA_OPERATIVA.md §5.2 «Implementaciones retenidas»; paso 24).

## API pública

- clase `Impl` _(línea 41)_
- `get(key, version=…)` — El Impl registrado o LookupError (una decisión que cita una implementación que este código ya no tiene). _(línea 108)_
- `resolve_stamp(stamp)` — 'run_checks@1' → Impl. Las acciones de la ontología ('CrearTesis@1') son escrituras, no cálculos: None. _(línea 116)_
- `missing_for(manifest)` — Etiquetas `impl` de un manifiesto que este código NO retiene (las de acciones de la ontología, 'CrearTesis@1', son escrituras y no cuentan; … _(línea 124)_
- `catalog(lang=…)` — Lista pública (para el 🩺 y las pruebas): qué implementaciones retiene este despliegue. _(línea 138)_
- `module_view(mod_name, arts, notes=…)` — SimpleNamespace con las funciones del módulo `mod_name` atadas a una COPIA de sus globales en la que las constantes de `governance.bind` … _(línea 153)_
- `view_with(view, **overrides)` — La misma vista con nombres reemplazados (p. ej. `trading_enabled` → el valor que regía): las funciones de la vista leen sus globales en … _(línea 182)_
- `under(arts)` — Este hilo lee `governance.param` desde `arts` (kernel.params, ontology.shapes, policy.gates…). _(línea 193)_
- `sha(obj)` _(línea 201)_
- `diff(a, b, path=…, out=…, limit=…)` — Diferencias campo a campo entre lo REGISTRADO (a) y lo REPETIDO (b): [{path, recorded, replayed}]. _(línea 207)_
- `golden_run(key, version, arts)` — Salida de `key@version` sobre entradas FIJAS (sin base, sin red) con los cuerpos `arts`. La prueba dorada compara su huella con … _(línea 245)_
- `repo_arts(selection=…)` — Cuerpos del repositorio (verificados por hash) del release propuesto (manifest.json, sin selección por entorno), con `selection` {aid: … _(línea 326)_

**Internas** (empiezan con `_`): `_bindings_for`, `_norm`, `_short`

## Depende de

- [[brokerage.risk.py]] — importa `(dinámico: brokerage.risk)`
- [[core.__init__.py]] — importa `engine`, `focus`, `report`
- [[core.decision_sites.py]] — importa `clean`
- [[core.decisions.py]] — importa `(dinámico: core.decisions)`, `canonical`
- [[core.governance.py]] — importa `governance`
- [[core.governance_flow.py]] — importa `(dinámico: core.governance_flow)`
- [[core.numbers.py]] — importa `(dinámico: core.numbers)`
- [[core.portfolio_advisor.py]] — importa `(dinámico: core.portfolio_advisor)`
- [[core.world.py]] — importa `(dinámico: core.world)`
- [[matrix.engine.py]] — importa `(dinámico: matrix.engine)`, `engine`
- [[research.committee.py]] — importa `(dinámico: research.committee)`

## Lo usan

- [[core.replay.py]] — lo importa
- [[scripts.build_impl_goldens.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_impl_registry.py]]
- [[tests.test_replay_determinism.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (h) — PASO 24 - REPETIR DECISIONES (replay), IMPLEMENTACIONES RETENIDAS]]
