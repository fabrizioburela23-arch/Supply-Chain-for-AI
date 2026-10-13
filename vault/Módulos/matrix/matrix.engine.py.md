---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "matrix/engine.py"
lenguaje: "python"
lineas: 769
aliases: ["matrix/engine.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# matrix/engine.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 769 líneas · `matrix/engine.py`

## Para qué sirve

construcción, modulación y propagación de matrices.

## API pública

- `bulk_weight_factor()` — Factor de descuento para links importados en bulto (1.0.0: 0.5 = 50 % del peso de una relación curada del mismo tipo), acotado a [0,1]. … _(línea 88)_
- `link_confidence(props)` — properties → confianza 0-1 o None (= sin dato, no se descuenta). Orden: confidence declarada > confirmado por una persona (status) / … _(línea 102)_
- `node_index(session, as_of=…)` — Índice estable id→posición (orden alfabético de ids de objetos). _(línea 189)_
- `build_matrices_from_triples(triples, idx, sparse=…)` — NÚCLEO NUMÉRICO puro (sin DB): {rel_type: matriz NxN} desde triples (source, target, rel, weight). Igual semántica que el histórico — … _(línea 224)_
- `build_matrices(session, as_of=…, sparse=…)` — {rel_type: matriz NxN} con A[i,j]=peso i→j (i PROVEE a j). _(línea 270)_
- `active_factors(session, as_of=…)` — Hiperaristas activas: objetos type='Factor' + links 'affects' vigentes. _(línea 295)_
- `fragility_cap()` — Tope de fragilidad POR NODO (`kernel.params.fragility_cap`; 1.0.0: 2.5). Con decenas de Factores latentes activos a la vez, la suma sin … _(línea 359)_
- `fragility(idx, factors)` — Vector de FRAGILIDAD por nodo (1.0 baseline). Cada hiperarista activa aumenta la fragilidad de sus miembros: f = 1 + Σ coef·(severity/5), … _(línea 368)_
- `modulate(mats, idx, factors)` — Compat: para el endpoint que muestra la matriz 'modulada', devuelve las matrices con las columnas de los miembros escaladas por su … _(línea 384)_
- `propagate(mats, idx, ids, shock_ids, magnitude=…, damping=…, max_hops=…, threshold=…, rel_weights=…, frag=…, nonlinear=…, eps=…, dt=…)` — EL kernel de propagación: shock en `shock_ids` → impacto 0..1 por nodo. _(línea 432)_
- `propagate_block(DT, frag, X0, damping=…, max_hops=…, threshold=…, nonlinear=…)` — EL MISMO kernel que `propagate`, en LOTE: cada columna de X0 (n×k) es un choque independiente. Las operaciones son las del bucle, en el … _(línea 486)_
- `propagate_many(mats, idx, ids, sources, magnitude=…, damping=…, max_hops=…, threshold=…, rel_weights=…, frag=…, nonlinear=…, dt=…, chunk=…)` — Choques de UN nodo para cada id de `sources`, en lote (vistas rápidas, INFRA_OPERATIVA §4.4). Devuelve {source_id: (impacts, hops)} con … _(línea 519)_
- `dependency_transpose(mats, rel_weights=…)` — Tᵀ lista para `propagate(..., dt=…)`: se calcula UNA vez y se reutiliza en todos los choques. _(línea 547)_
- `propagate_bands(mats, idx, ids, shock_ids, n_samples=…, seed=…, mag_sigma=…, frag_sigma=…, frag=…, **kw)` — BANDAS DE INCERTIDUMBRE Monte Carlo (spec §extensiones avanzadas, aditivo). Corre el kernel N veces perturbando la magnitud del shock y los … _(línea 552)_
- `pagerank(agg, alpha=…, tol=…, max_iter=…, personalization=…)` — PageRank ponderado sobre el grafo de DEPENDENCIA (agg.T): un nodo es central si MUCHOS (transitivamente) dependen de él — alinea con el … _(línea 589)_
- `spectral_radius(mats, factors=…, idx=…, rel_weights=…, damping=…)` — ρ(T): radio espectral de la matriz de transmisión EFECTIVA por hop (incluida la modulación por fragilidad si hay Factores activos). El … _(línea 633)_
- `compute_metrics(session, as_of=…)` — Métricas por nodo: grado in/out ponderado, tamaño de cascada (¿a cuántos arrastra si cae?), ranking de chokepoints y PageRank (centralidad … _(línea 700)_
- `graph_key(session)` — Clave de caché derivada del grafo: `g{graph_version}.l{linaje}.r{release[:8]}`. Una lectura por PK (~0,05 ms, sin degradarse con millones … _(línea 748)_

**Internas** (empiezan con `_`): `_utcnow`, `_use_sparse`, `_eff_weight`, `_issparse`, `_colsum`, `_rowsum`, `_scale_cols`, `_scale_rows`, `_transpose_csr`, `_iso_or_none`, `_dependency_matrix`, `_kp`, `_spectral_power_iter`, `_cache_get`, `_cache_set`

## Depende de

- [[core.__init__.py]] — importa `graph_key`
- [[core.governance.py]] — importa `governance`
- [[ontology.models.py]] — importa `LinkRecord`, `ObjectRecord`
- [[ontology.service.py]] — importa `_links_active_at`, `_parse_dt`
- [[ontology.vocabulary.py]] — importa `vocabulary`

## Lo usan

- [[core.geosit.py]] — lo importa
- [[matrix.api.py]] — lo importa
- [[matrix.tensor.py]] — lo importa
- [[ontology.bulk_import.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 20 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV MATRIX_ENGINE]]

## Pruebas que lo cubren

- [[tests.test_cleanup_server.py]]
- [[tests.test_governance.py]]
- [[tests.test_governance_seed_parity.py]]
- [[tests.test_hot_views_parity.py]]
- [[tests.test_infra.py]]
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
