# ESTADO — Khipus AI Finance Intelligence · Ontología (Palantir-style)

Archivo vivo. Cada sesión de trabajo en la ontología lee esto primero y lo
actualiza al terminar. Ver `ROADMAP_KHIPUS_ONTOLOGIA.md` (adjuntado por el
usuario) para el plan completo por fases, y `docs/AUDITORIA.md` para las
correcciones de arquitectura respecto al roadmap original (backend real =
Flask/Python, no Node; `/v1/*` ya es la API pública monetizada; Neo4j Aura ya
está conectado).

## Decisiones tomadas (no reabrir sin razón nueva)

1. **Base de datos de la ontología: Postgres en Railway.** Neo4j Aura se
   conserva como espejo de solo lectura del Grafo Temporal — no se apaga.
2. **Backend: Flask/Python**, no Node.js. SQLAlchemy en vez de Prisma,
   Pydantic en vez de Zod, APScheduler en vez de node-cron, pytest en vez de
   Vitest/Jest.
3. **Prefijo de API: `/api/ontology/*`** — NO `/v1/*` (ese ya es el producto
   de API pública monetizado por tiers, `khipu_auth()`).
4. **Despliegue incremental a `main`**: cambios aditivos, producción siempre
   verde. El switch del frontend a leer desde la API se hace solo tras
   verificar en producción que el grafo se ve idéntico.
5. **Migración del portafolio**: `MKT.pos` vive hoy en `localStorage`. Migra a
   la ontología (`Position`) en Fase 1/2 sin romper la UX mientras tanto.

## Fase 0 — AUDITORÍA Y PREPARACIÓN

**Estado: ✅ COMPLETA**

- [x] `docs/AUDITORIA.md` — inventario completo (dónde vive cada dato, APIs
      externas, tipos de objeto/relación implícitos, corrección de supuestos
      del roadmap).
- [x] `docs/ESTADO.md` — este archivo.
- [x] `scripts/export_graph_v0.js` — exportador fiel (replica merge/alias del
      navegador vía Node `vm`, mismo orden de carga que `<script src>`).
- [x] `data/grafo_v0.json` — snapshot: 463 nodos, 1163 links (100% resuelven),
      40 categorías, 14 pre-IPO, 105 hechos temporales, 32 objetos de
      ontología. Validado isomorfo con los contadores de producción.
- [x] Test desactualizado corregido (`test_health_has_app_name` afirmaba el
      nombre de marca antiguo). Suite: **18/18 pasan**.
- [x] Producción intacta (no se tocó `server.py` ni `app.html` de cara al
      usuario en esta fase, salvo el fix del test).

## Fase 1 — LA ONTOLOGÍA COMO BACKEND

**Estado: 🔜 SIGUIENTE**

Pendiente (ver roadmap para el detalle completo, adaptado a Flask/Postgres):
- [ ] Provisionar Postgres en Railway (usuario, con guía paso a paso).
- [ ] Esquema SQLAlchemy: `events` (append-only) + `objects`/`links`
      materializados, bitemporal (`valid_from/valid_to` + `recorded_at`).
- [ ] API `/api/ontology/*`: objects, objects/:id, objects/:id/links,
      objects/:id/history, graph?as_of=, graph/diff, POST events (interno,
      Fase 2 lo expone vía Acciones).
- [ ] Script de migración: lee `data/grafo_v0.json` → genera eventos
      `ObjectCreated`/`LinkCreated` con `valid_from` real.
- [ ] Frontend: cambiar UNA línea para cargar el grafo desde la API en vez
      del JSON embebido, comportamiento visual idéntico, verificar en
      producción antes de quitar el bundle JS del cliente.

## Fases 2-5

No iniciadas. Ver roadmap.

## Contexto de sesión previo a la ontología (para no reconstruir)

Antes de este roadmap, ya se había construido (y sigue en pie, se reusa como
semilla):
- **Grafo de Conocimiento Temporal** (`engine/temporal-graph.js`): timeline
  con validez, D3 force-graph, ficha de objeto con precio en vivo + NRS +
  Bixby análisis + noticias, microsimulación de shocks (BFS con dirección
  semántica), chokepoints, exposición de portafolio. Persiste opcionalmente
  en Neo4j Aura (ya conectado, badge "neo4j 🟢").
- **Ontología cliente** (`nodes/ontology.js` + `ontology_facts.js`): 8 tipos
  de objeto, 12 tipos de relación, 32 objetos no-empresa, 58 relaciones
  tipadas reales. Esto se convierte en parte de la semilla de migración de
  Fase 1, no se descarta.

## Cómo continuar en la próxima sesión

1. Lee este archivo + `docs/AUDITORIA.md` + `ROADMAP_KHIPUS_ONTOLOGIA.md`.
2. Confirma con el usuario si ya provisionó Postgres en Railway (paso manual
   suyo, como con Neo4j Aura).
3. Arranca Fase 1 en el orden del roadmap: esquema → migración → API de
   lectura → switch del frontend. Actualiza este archivo al cerrar.
