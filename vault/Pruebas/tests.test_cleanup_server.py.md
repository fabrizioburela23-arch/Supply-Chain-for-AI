---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_cleanup_server.py"
lenguaje: "python"
lineas: 231
aliases: ["tests/test_cleanup_server.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_cleanup_server.py

> Prueba · capa [[Capa Pruebas]] · 231 líneas · `tests/test_cleanup_server.py`

## Qué prueba

Limpieza 2026-10-11 ("que no queden cosas sueltas"), lado servidor. Cada prueba fija un arreglo del inventario para que la copia suelta no vuelva: §3 vocabulario re-escrito a mano · §8 preguntas abiertas guardadas como "errores" · §9 agente de noticias sin perfil en vivo y permisos que no coincidían · §13 el chat no podía abrir Cripto · §15 rutas sin candado o muertas · §21 restos (alias _claude_complete, precio de respaldo de Gemini, "skipped por presupuesto" por analista).

**14** funciones `test_…`.

## Cubre

- [[app.html]]
- [[core.agents_registry.py]]
- [[core.ai.py]]
- [[core.ai_usage.py]]
- [[core.http.py]]
- [[core.khipu_chat.py]]
- [[core.pin.py]]
- [[core.semantic.py]]
- [[core.sim_agents.py]]
- [[core.voice_agent.py]]
- [[core.voice_api.py]]
- [[core.world.py]]
- [[data.grafo_v0.json]]
- [[matrix.engine.py]]
- [[matrix.tensor.py]]
- [[mcp_server.tools.py]]
- [[ontology.db.py]]
- [[ontology.vocabulary.json]]
- [[ontology.vocabulary.py]]
- [[research.agents.registry.py]]
- [[research.analytics.py]]
- [[research.committee.py]]
- [[research.context.py]]
- [[research.models.py]]
- [[research.runner.py]]
- [[scripts.audit_graph.py]]
- [[server.py]]

## Rutas HTTP que llama

2 rutas, de los grupos: [[API diag]], [[API voice]]

## Variables de entorno que fija o nombra

[[ENV ELEVENLABS_KEY]], [[ENV MATRIX_ENGINE]], [[ENV TRADE_PIN]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 (b) — LIMPIEZA QUE NO QUEDEN COSAS SUELTAS (sw v254)]]
