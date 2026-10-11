---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "matrix/engine.py"
lenguaje: "python"
lineas: 710
aliases: ["matrix/engine.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# matrix/engine.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 710 líneas · `matrix/engine.py`

## Para qué sirve

construcción, modulación y propagación de matrices.

## API pública

- `bulk_weight_factor()` — Factor de descuento para links importados en bulto (default 0.5 = 50% del peso de una relación curada del mismo tipo). Parametrizable, NO … _(línea 78)_
- `link_confidence(props)` — properties → confianza 0-1 o None (= sin dato, no se descuenta). Orden: confidence declarada > confirmado por una persona (status) / … _(línea 99)_
- `node_index(session, as_of=…)` — Índice estable id→posición (orden alfabético de ids de objetos). _(línea 186)_
- `build_matrices_from_triples(triples, idx, sparse=…)` — NÚCLEO NUMÉRICO puro (sin DB): {rel_type: matriz NxN} desde triples (source, target, rel, weight). Igual semántica que el histórico — … _(línea 220)_
- `build_matrices(session, as_of=…, sparse=…)` — {rel_type: matriz NxN} con A[i,j]=peso i→j (i PROVEE a j). _(línea 266)_
- `active_factors(session, as_of=…)` — Hiperaristas activas: objetos type='Factor' + links 'affects' vigentes. _(línea 291)_
- `fragility_cap()` — Tope de fragilidad POR NODO (env FRAGILITY_CAP, default 2.5). Con decenas de Factores latentes activos a la vez, la suma sin tope pone el … _(línea 355)_
- `fragility(idx, factors)` — Vector de FRAGILIDAD por nodo (1.0 baseline). Cada hiperarista activa aumenta la fragilidad de sus miembros: f = 1 + Σ coef·(severity/5), … _(línea 368)_
- `modulate(mats, idx, factors)` — Compat: para el endpoint que muestra la matriz 'modulada', devuelve las matrices con las columnas de los miembros escaladas por su … _(línea 384)_
- `propagate(mats, idx, ids, shock_ids, magnitude=…, damping=…, max_hops=…, threshold=…, rel_weights=…, frag=…, nonlinear=…, eps=…, dt=…)` — EL kernel de propagación: shock en `shock_ids` → impacto 0..1 por nodo. _(línea 427)_
- `dependency_transpose(mats, rel_weights=…)` — Tᵀ lista para `propagate(..., dt=…)`: se calcula UNA vez y se reutiliza en todos los choques. _(línea 480)_
- `propagate_bands(mats, idx, ids, shock_ids, n_samples=…, seed=…, mag_sigma=…, frag_sigma=…, frag=…, **kw)` — BANDAS DE INCERTIDUMBRE Monte Carlo (spec §extensiones avanzadas, aditivo). Corre el kernel N veces perturbando la magnitud del shock y los … _(línea 485)_
- `pagerank(agg, alpha=…, tol=…, max_iter=…, personalization=…)` — PageRank ponderado sobre el grafo de DEPENDENCIA (agg.T): un nodo es central si MUCHOS (transitivamente) dependen de él — alinea con el … _(línea 521)_
- `spectral_radius(mats, factors=…, idx=…, rel_weights=…, damping=…)` — ρ(T): radio espectral de la matriz de transmisión EFECTIVA por hop (incluida la modulación por fragilidad si hay Factores activos). El … _(línea 564)_
- `compute_metrics(session, as_of=…)` — Métricas por nodo: grado in/out ponderado, tamaño de cascada (¿a cuántos arrastra si cae?), ranking de chokepoints y PageRank (centralidad … _(línea 630)_

**Internas** (empiezan con `_`): `_utcnow`, `_use_sparse`, `_eff_weight`, `_issparse`, `_colsum`, `_rowsum`, `_scale_cols`, `_scale_rows`, `_transpose_csr`, `_iso_or_none`, `_dependency_matrix`, `_spectral_power_iter`, `_graph_epoch`, `_cache_get`, `_cache_set`

## Depende de

- [[ontology.models.py]] — importa `Event`, `LinkRecord`, `ObjectRecord`
- [[ontology.service.py]] — importa `_links_active_at`, `_parse_dt`
- [[ontology.vocabulary.py]] — importa `vocabulary`

## Lo usan

- [[core.geosit.py]] — lo importa
- [[matrix.api.py]] — lo importa
- [[matrix.tensor.py]] — lo importa
- [[ontology.bulk_import.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 12 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV FRAGILITY_CAP]]
- [[ENV IMPORT_BULK_WEIGHT_FACTOR]]
- [[ENV MATRIX_ENGINE]]

## Pruebas que lo cubren

- [[tests.test_cleanup_server.py]]
- [[tests.test_infra.py]]
- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_khipus_os_perf.py]]
- [[tests.test_matrix.py]]
- [[tests.test_matrix_sparse.py]]
- [[tests.test_ontology_actions.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_repair_review2.py]]
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
