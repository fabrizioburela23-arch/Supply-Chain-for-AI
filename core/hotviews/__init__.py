"""core/hotviews — vistas de camino crítico (docs/INFRA_OPERATIVA.md §4).

Vista = Φ(L, graph_version, release): una función pura y versionada de la verdad (Postgres; sin
DATABASE_URL, el snapshot data/grafo_v0.json con el MISMO código). Un solo constructor (un hilo), un
solo kernel (matrix.engine.propagate / propagate_many), intercambio atómico de una Generation inmutable.

Este paquete se importa desde ontology/service.py (por `signals`), así que este __init__ NO importa
numpy ni nada pesado. API:

    from core.hotviews import signals          # graph_version al confirmar, señales, linaje
    from core.hotviews import registry         # generation() / status()
    from core.hotviews import builder          # start() / request_build() / wait_for()
"""
