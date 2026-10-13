---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/actions.py"
lenguaje: "python"
lineas: 751
aliases: ["ontology/actions.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/actions.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 751 líneas · `ontology/actions.py`

## Para qué sirve

Fase 2 del roadmap: Acciones, el ADN de "escritura auditada" de Palantir. El usuario deja de solo mirar: registra tesis, anotaciones, correcciones y decisiones que se vuelven parte de la ontología, con autor, fecha y razonamiento — nunca un UPDATE silencioso.

## API pública

- clase `ActionError` _(línea 28)_
- clase `FuenteCitada` — Fuente citable de una tesis (Track C, Investigador Autónomo): la regla del proyecto es que toda cifra venga de una fuente verificable, no … _(línea 34)_
- clase `CrearTesisInput` _(línea 46)_
- clase `AnotarObjetoInput` _(línea 58)_
- clase `MarcarRiesgoInput` _(línea 63)_
- clase `ProponerVinculoInput` _(línea 69)_
- clase `ResolverVinculoInput` _(línea 77)_
- clase `RegistrarDecisionInput` _(línea 81)_
- clase `AjustarPosicionInput` _(línea 87)_
- clase `CorregirDatoInput` _(línea 94)_
- clase `IncorporarEmpresaInput` — Alta de una empresa nueva detectada en vivo (Radar). Reversible con RetirarEmpresa; todo queda como eventos inmutables. _(línea 101)_
- clase `RetractarVinculoInput` — G2: retracta UNA fila concreta de `links` (por su id) con un LinkRemoved DIRIGIDO (retracts_event_id). A diferencia de RechazarVinculo, no … _(línea 120)_
- clase `FusionarEntidadInput` — G2: fusiona un objeto duplicado (alias) en el canónico: el alias queda retired + merged_into, sus vínculos vigentes se retractan (dirigido, … _(línea 128)_
- clase `RetirarEmpresaInput` — Baja lógica (reversible): marca retired=true; el objeto y su historia quedan intactos en la ontología. _(línea 139)_
- clase `CrearFactorInput` — Crea una HIPERARISTA (Factor): un golpe que toca a VARIAS empresas a la vez (sanción, escasez de HBM, conflicto). El motor de matrices lo … _(línea 147)_
- clase `RetirarFactorInput` — Expira una hiperarista: cierra sus links 'affects' (valid_to). La historia queda en events — consultable as_of para verla activa antes de … _(línea 165)_
- clase `ActivarFactorInput` — Sube un Factor de su nivel LATENTE a su nivel de crisis, de forma PERSISTENTE y auditada. _(línea 172)_
- clase `DesactivarFactorInput` — Devuelve un Factor activado a su severidad latente (la que tenía antes de ActivarFactor; 1.0 si no hay registro). NO lo expira — para eso … _(línea 188)_
- `crear_tesis(session, inp, actor)` _(línea 220)_
- `anotar_objeto(session, inp, actor)` _(línea 264)_
- `marcar_riesgo(session, inp, actor)` _(línea 278)_
- `proponer_vinculo(session, inp, actor)` _(línea 289)_
- `retractar_vinculo(session, inp, actor, source=…, log=…)` — G2: LinkRemoved dirigido a la creación de ESTA fila. _(línea 362)_
- `fusionar_entidad(session, inp, actor, source=…)` — G2: alias → canónico, todo por eventos. Devuelve cuántos vínculos se movieron. _(línea 391)_
- `confirmar_vinculo(session, inp, actor)` _(línea 437)_
- `rechazar_vinculo(session, inp, actor)` _(línea 441)_
- `registrar_decision(session, inp, actor)` _(línea 445)_
- `ajustar_posicion(session, inp, actor)` _(línea 463)_
- `corregir_dato(session, inp, actor)` _(línea 491)_
- `incorporar_empresa(session, inp, actor)` — Alta viva de empresa (Radar/humano). Crea el objeto + link opcional al grafo. Falla si el id ya existe (usar CorregirDato para actualizar). _(línea 505)_
- `retirar_empresa(session, inp, actor)` — Baja lógica reversible: properties.retired = true/false. La historia completa queda en events — nada se borra jamás. _(línea 567)_
- `crear_factor(session, inp, actor)` — Crea la hiperarista: un ObjectRecord type='Factor' (con severity) + N links 'affects' bitemporales hacia las empresas afectadas. Solo … _(línea 582)_
- `retirar_factor(session, inp, actor)` — Expira la hiperarista: cierra los 'affects' vigentes (valid_to) y marca el Factor como expirado. Reversible en el sentido bitemporal (la … _(línea 615)_
- `activar_factor(session, inp, actor)` — Persistente: cambia `severity` en las props del Factor. El motor lo lee en active_factors() y el caché de matrices se invalida solo (la … _(línea 642)_
- `desactivar_factor(session, inp, actor)` — Revierte ActivarFactor. Vuelve a `severity_latente`; si el factor nunca se activó por esta vía (p.ej. venía de la ingesta multicapa) cae a … _(línea 678)_
- `execute_action(session, action_type, payload, actor)` — Punto de entrada único: valida con el esquema del catálogo y ejecuta. Lanza ActionError/ValidationError si algo no es válido — nunca … _(línea 723)_
- `list_actions(session, actor=…, action_type=…, object_id=…, limit=…)` — Para el panel '📋 Registro': timeline de ActionExecuted, filtrable. _(línea 740)_

**Internas** (empiezan con `_`): `_log_action`, `_require_object`, `_resolver_vinculo`, `_link_by_id`, `_proponer_por_tensor`, `_require_factor`

## Depende de

- [[matrix.tensor.py]] — importa `tensor`
- [[ontology.models.py]] — importa `Event`, `LinkRecord`, `ObjectRecord`
- [[ontology.provenance.py]] — importa `link_evidence`, `register_source`
- [[ontology.service.py]] — importa `OntologyError`, `_creation_event_for`, `_utcnow`, `apply_event`

## Lo usan

- [[ontology.agents.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[ontology.reconcile.py]] — lo importa

_Además lo importan 15 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_docs_facts.py]]
- [[tests.test_hot_invalidation.py]]
- [[tests.test_infra.py]]
- [[tests.test_investigador.py]]
- [[tests.test_matrix.py]]
- [[tests.test_ontology.py]]
- [[tests.test_ontology_actions.py]]
- [[tests.test_ontology_agents.py]]
- [[tests.test_ops_graph_version.py]]
- [[tests.test_ops_link_status_event.py]]
- [[tests.test_provenance.py]]
- [[tests.test_repair_ontology.py]]
- [[tests.test_repair_ontology_review.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_tensor_autolink.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-21 — Limpieza estructural - Track A Fase 2 + Track B completos]]
- [[Sesión 2026-07-10 — modo máximo (feedback - perfeccionar Khipu, 555 empresas, vivo, 3D)]]
