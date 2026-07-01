# Grafo Temporal persistente en Neo4j — YA IMPLEMENTADO

## Qué se hizo (no necesitas Cowork ni pasos de código)

El Grafo de Conocimiento Temporal ahora **persiste en Neo4j** directamente, con
el driver oficial. **No se usa Graphiti** a propósito: Graphiti necesitaría un
proveedor de *embeddings* aparte (OpenAI/Voyage — Anthropic no ofrece embeddings)
y sirve para *extraer* entidades de texto libre, pero nuestros hechos ya vienen
estructurados (sujeto → relación → objeto, con fechas). Escribir directo a Neo4j
es más simple, robusto, sin costo de tokens y sin API keys extra.

### Cambios en el repo (ya commiteados)
- `requirements.txt`: se agregó `neo4j>=5.14.0` (driver ligero).
- `server.py`:
  - `_neo4j_available()` / `_temporal_mode()` → detectan Neo4j por las env vars.
  - `_get_neo4j_driver()` → driver singleton + constraints (una sola vez).
  - `_neo4j_add_fact(fact)` → MERGE idempotente: `(:Entity)-[:ASSERTS]->(:Fact)-[:ABOUT]->(:Entity)`
    guardando la ventana de validez (`valid_from` → `valid_until`).
  - `/api/grafo/seed` → carga masiva de hechos (idempotente).
- `engine/temporal-graph.js`: al detectar Neo4j conectado, siembra automáticamente
  los ~34 hechos derivados una vez (guardia en localStorage; el MERGE del server
  igual evita duplicados).

## Lo único que TÚ ya hiciste
Poner en Railway → Variables:
```
NEO4J_URI=neo4j+s://c54f726c.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<tu contraseña de Aura>
```

## Cómo verificar que quedó activo
1. Espera el redeploy de Railway (~2-3 min; instala el driver `neo4j`).
2. Abre la app en incógnito → pestaña **◈ Grafo Temporal**.
3. El badge arriba a la derecha debe pasar de *"memoria: nativa"* a
   **"memoria: neo4j 🟢 (N hechos)"**.
4. (Opcional) En el panel de Neo4j Aura → **Query** → corre:
   ```cypher
   MATCH (f:Fact) RETURN count(f);
   MATCH (a:Entity)-[:ASSERTS]->(f:Fact)-[:ABOUT]->(b:Entity)
   RETURN a.label, f.predicate, b.label LIMIT 25;
   ```
   Deberías ver los hechos (TSMC → fabrica → Nvidia, Huawei → sancionada, etc.).

## Si el badge NO cambia a neo4j 🟢
Abre 🩺 (diagnóstico) → busca "grafo". Te dirá una de:
- *"Neo4j conectado"* → todo bien.
- *"NEO4J configurado pero no conecta: …"* → revisa que el `NEO4J_URI` empiece con
  `neo4j+s://` y que la contraseña sea la correcta (resetéala en Aura si dudas).
- *"modo NATIVO"* → las env vars no llegaron a Railway (revisa nombres exactos:
  `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`).

## Nota sobre tu instancia
Es **AuraDB Professional (trial 14 días)**. Funciona perfecto ahora. Si en 2
semanas no quieres que cobre, crea una **AuraDB Free** y cambia las 3 variables.
Si Neo4j se cae o expira, la app **sigue funcionando en modo nativo** sin romperse.
