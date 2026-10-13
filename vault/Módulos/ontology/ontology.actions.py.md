---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/actions.py"
lenguaje: "python"
lineas: 825
aliases: ["ontology/actions.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/actions.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 825 líneas · `ontology/actions.py`

## Para qué sirve

Fase 2 del roadmap: Acciones, el ADN de "escritura auditada" de Palantir. El usuario deja de solo mirar: registra tesis, anotaciones, correcciones y decisiones que se vuelven parte de la ontología, con autor, fecha y razonamiento — nunca un UPDATE silencioso.

## API pública

- clase `ActionError` _(línea 34)_
- clase `FuenteCitada` — Fuente citable de una tesis (Track C, Investigador Autónomo): la regla del proyecto es que toda cifra venga de una fuente verificable, no … _(línea 40)_
- clase `CrearTesisInput` _(línea 52)_
- clase `AnotarObjetoInput` _(línea 64)_
- clase `MarcarRiesgoInput` _(línea 69)_
- clase `ProponerVinculoInput` _(línea 75)_
- clase `ResolverVinculoInput` _(línea 83)_
- clase `RegistrarDecisionInput` _(línea 87)_
- clase `AjustarPosicionInput` _(línea 93)_
- clase `CorregirDatoInput` _(línea 100)_
- clase `IncorporarEmpresaInput` — Alta de una empresa nueva detectada en vivo (Radar). Reversible con RetirarEmpresa; todo queda como eventos inmutables. _(línea 107)_
- clase `RetractarVinculoInput` — G2: retracta UNA fila concreta de `links` (por su id) con un LinkRemoved DIRIGIDO (retracts_event_id). A diferencia de RechazarVinculo, no … _(línea 126)_
- clase `FusionarEntidadInput` — G2: fusiona un objeto duplicado (alias) en el canónico: el alias queda retired + merged_into, sus vínculos vigentes se retractan (dirigido, … _(línea 134)_
- clase `RetirarEmpresaInput` — Baja lógica (reversible): marca retired=true; el objeto y su historia quedan intactos en la ontología. _(línea 145)_
- clase `CrearFactorInput` — Crea una HIPERARISTA (Factor): un golpe que toca a VARIAS empresas a la vez (sanción, escasez de HBM, conflicto). El motor de matrices lo … _(línea 153)_
- clase `RetirarFactorInput` — Expira una hiperarista: cierra sus links 'affects' (valid_to). La historia queda en events — consultable as_of para verla activa antes de … _(línea 171)_
- clase `ActivarFactorInput` — Sube un Factor de su nivel LATENTE a su nivel de crisis, de forma PERSISTENTE y auditada. _(línea 178)_
- clase `DesactivarFactorInput` — Devuelve un Factor activado a su severidad latente (la que tenía antes de ActivarFactor; 1.0 si no hay registro). NO lo expira — para eso … _(línea 194)_
- `crear_tesis(session, inp, actor)` _(línea 250)_
- `anotar_objeto(session, inp, actor)` _(línea 294)_
- `marcar_riesgo(session, inp, actor)` _(línea 308)_
- `proponer_vinculo(session, inp, actor)` _(línea 319)_
- `retractar_vinculo(session, inp, actor, source=…, log=…)` — G2: LinkRemoved dirigido a la creación de ESTA fila. _(línea 392)_
- `fusionar_entidad(session, inp, actor, source=…)` — G2: alias → canónico, todo por eventos. Devuelve cuántos vínculos se movieron. _(línea 421)_
- `confirmar_vinculo(session, inp, actor)` _(línea 467)_
- `rechazar_vinculo(session, inp, actor)` _(línea 471)_
- `registrar_decision(session, inp, actor)` _(línea 475)_
- `ajustar_posicion(session, inp, actor)` _(línea 498)_
- `corregir_dato(session, inp, actor)` _(línea 526)_
- `incorporar_empresa(session, inp, actor)` — Alta viva de empresa (Radar/humano). Crea el objeto + link opcional al grafo. Falla si el id ya existe (usar CorregirDato para actualizar). _(línea 540)_
- `retirar_empresa(session, inp, actor)` — Baja lógica reversible: properties.retired = true/false. La historia completa queda en events — nada se borra jamás. _(línea 602)_
- `crear_factor(session, inp, actor)` — Crea la hiperarista: un ObjectRecord type='Factor' (con severity) + N links 'affects' bitemporales hacia las empresas afectadas. Solo … _(línea 617)_
- `retirar_factor(session, inp, actor)` — Expira la hiperarista: cierra los 'affects' vigentes (valid_to) y marca el Factor como expirado. Reversible en el sentido bitemporal (la … _(línea 650)_
- `activar_factor(session, inp, actor)` — Persistente: cambia `severity` en las props del Factor. El motor lo lee en active_factors() y el caché de matrices se invalida solo (la … _(línea 677)_
- `desactivar_factor(session, inp, actor)` — Revierte ActivarFactor. Vuelve a `severity_latente`; si el factor nunca se activó por esta vía (p.ej. venía de la ingesta multicapa) cae a … _(línea 713)_
- `execute_action(session, action_type, payload, actor, principal=…, meta=…, correlation_id=…)` — Punto de entrada único: valida con el esquema del catálogo y ejecuta. Lanza ActionError/ValidationError si algo no es válido — nunca … _(línea 776)_
- `list_actions(session, actor=…, action_type=…, object_id=…, limit=…)` — Para el panel '📋 Registro': timeline de ActionExecuted, filtrable. _(línea 813)_

**Internas** (empiezan con `_`): `_log_action`, `_decision_marks`, `_cite`, `_require_object`, `_resolver_vinculo`, `_link_by_id`, `_proponer_por_tensor`, `_require_factor`, `_subject`

## Depende de

- [[core.decisions.py]] — importa `decisions`
- [[core.identity.py]] — importa `identity`
- [[matrix.tensor.py]] — importa `tensor`
- [[ontology.models.py]] — importa `Event`, `LinkRecord`, `ObjectRecord`
- [[ontology.provenance.py]] — importa `link_evidence`, `register_source`
- [[ontology.service.py]] — importa `OntologyError`, `_creation_event_for`, `_utcnow`, `apply_event`

## Lo usan

- [[ontology.agents.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[ontology.reconcile.py]] — lo importa

_Además lo importan 20 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_docs_facts.py]]
- [[tests.test_hot_invalidation.py]]
- [[tests.test_infra.py]]
- [[tests.test_investigador.py]]
- [[tests.test_ledger_chain.py]]
- [[tests.test_ledger_core.py]]
- [[tests.test_matrix.py]]
- [[tests.test_ontology.py]]
- [[tests.test_ontology_actions.py]]
- [[tests.test_ontology_agents.py]]
- [[tests.test_ops_graph_version.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_ops_link_status_event.py]]
- [[tests.test_ops_review_steps568.py]]
- [[tests.test_ops_single_source.py]]
- [[tests.test_provenance.py]]
- [[tests.test_repair_ontology.py]]
- [[tests.test_repair_ontology_review.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_tensor_autolink.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-21 — Limpieza estructural - Track A Fase 2 + Track B completos]]
- [[Sesión 2026-07-10 — modo máximo (feedback - perfeccionar Khipu, 555 empresas, vivo, 3D)]]
