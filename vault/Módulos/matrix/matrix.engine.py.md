---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "matrix/engine.py"
lenguaje: "python"
lineas: 957
aliases: ["matrix/engine.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# matrix/engine.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 957 líneas · `matrix/engine.py`

## Para qué sirve

construcción, modulación y propagación de matrices.

## API pública

- `bulk_weight_factor()` — Factor de descuento para links importados en bulto (1.0.0: 0.5 = 50 % del peso de una relación curada del mismo tipo), acotado a [0,1]. … _(línea 102)_
- `link_confidence(props)` — properties → confianza 0-1 o None (= sin dato, no se descuenta). Orden: confidence declarada > confirmado por una persona (status) / … _(línea 116)_
- `node_index(session, as_of=…, known=…)` — Índice estable id→posición (orden alfabético de ids de objetos). _(línea 203)_
- `build_matrices_from_triples(triples, idx, sparse=…)` — NÚCLEO NUMÉRICO puro (sin DB): {rel_type: matriz NxN} desde triples (source, target, rel, weight). Igual semántica que el histórico — … _(línea 248)_
- `build_matrices(session, as_of=…, sparse=…, known=…)` — {rel_type: matriz NxN} con A[i,j]=peso i→j (i PROVEE a j). _(línea 294)_
- `active_factors(session, as_of=…, known=…)` — Hiperaristas activas: objetos type='Factor' + links 'affects' vigentes. _(línea 329)_
- `factor_coef(raw)` — Coeficiente de un miembro de un factor (peso del vínculo 'affects'). 1.0.0: `float(w or 1)` — un 0 se volvía 1 (+100 % de sensibilidad). … _(línea 437)_
- `factor_severity(raw)` — Severidad de un factor. 1.0.0: ausente → 5. 2.0.0 (`factor_inputs_strict`, PROP-20): ausente → la severidad LATENTE … _(línea 448)_
- `fragility_cap()` — Tope de fragilidad POR NODO (`kernel.params.fragility_cap`; 1.0.0: 2.5). Con decenas de Factores latentes activos a la vez, la suma sin … _(línea 463)_
- `fragility(idx, factors)` — Vector de FRAGILIDAD por nodo (1.0 baseline). Cada hiperarista activa aumenta la fragilidad de sus miembros: f = 1 + Σ coef·(severity/5), … _(línea 472)_
- `modulate(mats, idx, factors)` — Compat: para el endpoint que muestra la matriz 'modulada', devuelve las matrices con las columnas de los miembros escaladas por su … _(línea 489)_
- `persistent_source()` — ¿La fuente del choque PERSISTE en cada salto (PROP-08)? kernel.params 2.1.0 `propagation: 'persistent'`; 1.0.0 y 2.0.0 no traen la clave → … _(línea 551)_
- `propagate(mats, idx, ids, shock_ids, magnitude=…, damping=…, max_hops=…, threshold=…, rel_weights=…, frag=…, nonlinear=…, eps=…, dt=…, x0=…, direction=…)` — EL kernel de propagación: shock en `shock_ids` → impacto 0..1 por nodo. _(línea 567)_
- `propagate_block(DT, frag, X0, damping=…, max_hops=…, threshold=…, nonlinear=…)` — EL MISMO kernel que `propagate`, en LOTE: cada columna de X0 (n×k) es un choque independiente. Las operaciones son las del bucle, en el … _(línea 643)_
- `propagate_many(mats, idx, ids, sources, magnitude=…, damping=…, max_hops=…, threshold=…, rel_weights=…, frag=…, nonlinear=…, dt=…, chunk=…)` — Choques de UN nodo para cada id de `sources`, en lote (vistas rápidas, INFRA_OPERATIVA §4.4). Devuelve {source_id: (impacts, hops)} con … _(línea 682)_
- `dependency_transpose(mats, rel_weights=…, direction=…)` — Tᵀ lista para `propagate(..., dt=…)`: se calcula UNA vez y se reutiliza en todos los choques. direction='up' (auge de demanda) solo si el … _(línea 710)_
- `direction_up_enabled()` — ¿El release vigente calcula AUGES de demanda (cliente → proveedor) con el kernel? 1.0.0: no (la API lo dice con honestidad: 'unsupported'); … _(línea 718)_
- `chokepoint_order(metrics, sums)` — Orden del ranking de cuellos de botella (kernel.params.chokepoint_rank_by). 1.0.0 'count': por cantidad de empresas golpeadas ≥ 1 % (orden … _(línea 724)_
- `propagate_bands(mats, idx, ids, shock_ids, n_samples=…, seed=…, mag_sigma=…, frag_sigma=…, frag=…, **kw)` — BANDAS DE INCERTIDUMBRE Monte Carlo (spec §extensiones avanzadas, aditivo). Corre el kernel N veces perturbando la magnitud del shock y los … _(línea 734)_
- `pagerank(agg, alpha=…, tol=…, max_iter=…, personalization=…)` — PageRank ponderado sobre el grafo de DEPENDENCIA (agg.T): un nodo es central si MUCHOS (transitivamente) dependen de él — alinea con el … _(línea 771)_
- `spectral_radius(mats, factors=…, idx=…, rel_weights=…, damping=…)` — ρ(T): radio espectral de la matriz de transmisión EFECTIVA por hop (incluida la modulación por fragilidad si hay Factores activos). El … _(línea 815)_
- `compute_metrics(session, as_of=…, known=…)` — Métricas por nodo: grado in/out ponderado, tamaño de cascada (¿a cuántos arrastra si cae?), ranking de chokepoints y PageRank (centralidad … _(línea 884)_
- `graph_key(session)` — Clave de caché derivada del grafo: `g{graph_version}.l{linaje}.r{release[:8]}`. Una lectura por PK (~0,05 ms, sin degradarse con millones … _(línea 936)_

**Internas** (empiezan con `_`): `_P`, `_damage_rels`, `_utcnow`, `_use_sparse`, `_eff_weight`, `_issparse`, `_colsum`, `_rowsum`, `_scale_cols`, `_scale_rows`, `_transpose_csr`, `_active_factors_known`, `_canonical_factors`, `_iso_or_none`, `_dependency_matrix`, `_kp`, `_nonlinear`, `_spectral_power_iter`, `_cache_get`, `_cache_set`

## Depende de

- [[core.__init__.py]] — importa `graph_key`
- [[core.governance.py]] — importa `governance`
- [[ontology.bitemporal.py]] — importa `bitemporal`
- [[ontology.models.py]] — importa `LinkRecord`, `ObjectRecord`
- [[ontology.service.py]] — importa `_links_active_at`, `_parse_dt`
- [[ontology.vocabulary.py]] — importa `vocabulary`

## Lo usan

- [[core.geosit.py]] — lo importa
- [[core.governance_flow.py]] — lo importa
- [[core.governance_preview.py]] — lo importa
- [[core.impls.py]] — lo importa
- [[core.replay.py]] — lo importa
- [[core.scenario_engine.py]] — lo importa
- [[core.sim_agents.py]] — lo importa
- [[matrix.api.py]] — lo importa
- [[matrix.tensor.py]] — lo importa
- [[ontology.actions.py]] — lo importa
- [[ontology.bulk_import.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 29 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV MATRIX_ENGINE]]

## Pruebas que lo cubren

- [[tests.test_bitemporal.py]]
- [[tests.test_bitemporal_review.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_governance.py]]
- [[tests.test_governance_activation.py]]
- [[tests.test_governance_flow.py]]
- [[tests.test_governance_seed_parity.py]]
- [[tests.test_hot_views_parity.py]]
- [[tests.test_impl_registry.py]]
- [[tests.test_infra.py]]
- [[tests.test_kernel_monotone_edges.py]]
- [[tests.test_kernel_monotone_severity.py]]
- [[tests.test_kernel_reference_figures.py]]
- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_khipus_os_perf.py]]
- [[tests.test_matrix.py]]
- [[tests.test_matrix_sparse.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_ontology_actions.py]]
- [[tests.test_ops_graph_version.py]]
- [[tests.test_ops_link_status_event.py]]
- [[tests.test_ops_single_source.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_replay_determinism.py]]
- [[tests.test_review_infra_c.py]]
- [[tests.test_tensor.py]]
- [[tests.test_tensor_autolink.py]]
- [[tests.test_vocabulary.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (gg) — DIRECCIONES AL REVÉS + PESO DE LICENCIAS + PISO DEL KERNEL]]
- [[Sesión 2026-10-04 (h) — MISIÓN DE REPARACIÓN P0 INVESTIGACIÓN (R1-R6, sw v201)]]
- [[Sesión 2026-10-03 — GASTO DE IA, SIM. ESTRUCTURAL, AVATARES, CANVAS, COMITÉ DE CARTERA]]
- [[Sesión 2026-08-02 — Expansión multicapa COMPLETA (olas 1-6) - 949 nodos, 13 sectores, 70]]
- [[Sesión 2026-07-19 — Motor de matrices DISPERSAS + centralidad]]
- [[Sesión 2026-07-07 — Etapa 3 — Motor de matrices + hiperaristas - NÚCLEO COMPLETO]]
