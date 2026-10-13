---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_scenario_kernel.py"
lenguaje: "python"
lineas: 112
aliases: ["tests/test_scenario_kernel.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_scenario_kernel.py

> Prueba · capa [[Capa Pruebas]] · 112 líneas · `tests/test_scenario_kernel.py`

## Qué prueba

INFRA_OPERATIVA paso 12 (PROP-09/10, L4-03/04, L4-M2): con kernel.params@2.0.0 los escenarios solo SIEMBRAN y propaga EL kernel; en la simulación por agentes los % salen del kernel y la IA solo narra. Con 1.0.0 (vigente) todo queda como hoy (la BFS propia se conserva como implementación retenida de 1.0.0).

**5** funciones `test_…`.

## Cubre

- [[core.__init__.py]]
- [[core.ai.py]]
- [[core.governance.py]]
- [[core.scenario_engine.py]]
- [[core.semantic.py]]
- [[core.sim_agents.py]]
- [[ontology.vocabulary.py]]
