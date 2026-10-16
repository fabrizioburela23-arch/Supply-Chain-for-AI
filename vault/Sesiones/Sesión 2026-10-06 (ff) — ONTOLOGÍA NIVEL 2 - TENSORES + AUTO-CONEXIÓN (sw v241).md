---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-06"
ruta: "docs/ESTADO.md#L945"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-06 (ff) — ONTOLOGÍA NIVEL 2: TENSORES + AUTO-CONEXIÓN (sw v241)

> Sesión de trabajo · `docs/ESTADO.md` línea 945 (29 líneas) · [[Índice de sesiones]]

## Resumen

\- `matrix/tensor.py` (sin BD, lee data/grafo_v0.json): A ∈ ℝ^{R×N×N} (solo relaciones de FLUJO, peso×conf), D = transmisión del kernel (engine._dependency_matrix), Ψ = influencia de TODAS las fuentes a la vez (misma semántica que engine.propagate — test de paridad), c = caps en vivo → valuación verificada, X = rasgos z-normalizados + perfil estructural. Construye en ~0,4 s; caché por (mtime snapshot, caps as_of).

## Archivos que menciona

- [[core.world.py]]
- [[data.grafo_v0.json]]
- [[matrix.tensor.py]]
- [[matrix.tensor_api.py]]
- [[ontology.vocabulary.json]]
- [[scripts.audit_graph.py]]
- [[tests.test_tensor.py]]
- [[tests.test_tensor_autolink.py]]

← más antigua: [[Sesión 2026-10-06 (ee) — MAPA POR CAPITALIZACIÓN EN VIVO + HOME CON CADA CARTERA (sw v240)]] · más nueva: [[Sesión 2026-10-06 (gg) — DIRECCIONES AL REVÉS + PESO DE LICENCIAS + PISO DEL KERNEL]] →
