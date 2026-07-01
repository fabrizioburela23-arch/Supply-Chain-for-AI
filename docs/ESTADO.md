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

**Estado: ✅ COMPLETA (el núcleo bitemporal + API) · ⏸️ un paso a propósito diferido**

- [x] Esquema SQLAlchemy (`ontology/models.py`): `events` (append-only,
      bitemporal `valid_from/valid_to` + `recorded_at`) + `objects`/`links`
      materializados para lectura rápida.
- [x] `ontology/service.py`: `apply_event()` (inserta + materializa),
      `as_of_graph()` (time-travel real por VALIDEZ, reconstruido desde
      `events`, no desde la tabla materializada), `diff_graph()` (qué
      apareció/desapareció entre dos fechas), `object_history()`.
- [x] API `/api/ontology/*` (`ontology/api.py`, registrada como blueprint):
      `/status`, `/objects`, `/objects/:id`, `/objects/:id/links`,
      `/objects/:id/history`, `/graph?as_of=`, `/graph/diff?from=&to=`,
      `POST /events` (escritura de bajo nivel; Fase 2 la envuelve con el
      catálogo de Acciones).
- [x] **Prefijo `/api/ontology/*`**, no `/v1/*` (ese es el producto de API
      pública monetizado — ver `docs/AUDITORIA.md`).
- [x] Degradación elegante: sin `DATABASE_URL`, todo el resto de la app sigue
      funcionando igual (mismo patrón que Neo4j); `server.py` importa el
      blueprint en un try/except defensivo.
- [x] Script de migración `scripts/migrate_v0_to_ontology.py`: lee
      `data/grafo_v0.json` → genera eventos reales. **Reglas de fecha
      documentadas en el propio script** (empresas y links crudos sin fecha
      propia → GENESIS 2000-01-01; los 86 hechos temporales curados usan su
      `valid_from/valid_until` real).
- [x] **Validado end-to-end contra Postgres real** (local, para desarrollo):
      463 empresas + 32 objetos de ontología = 495 objetos; 0 ids sin
      resolver en la migración; time-travel correcto en ambas direcciones
      (ej. `as_of` antes/después de la sanción a Huawei 2019-05-16 y de la
      pérdida de Qualcomm-Huawei 2021-06-30); `diff()` detecta ambos cambios.
- [x] Tests: `tests/test_ontology.py` (8 tests: creación/actualización de
      objeto, links, time-travel antes/después, cierre de intervalo con
      LinkRemoved, diff añadido/quitado, historia ordenada, **migración
      isomorfa** — corre el script real y compara conteos con el snapshot).
      Se auto-saltan (skip) si no hay `DATABASE_URL` — no rompen CI sin DB.
- [x] `docs/AUDITORIA.md` documenta la corrección de arquitectura (Flask no
      Node, prefijo de API, Neo4j ya conectado se mantiene como espejo).

### ⏸️ Diferido a propósito (no es un olvido — es una decisión registrada)

**El swap completo del frontend** ("cambiar UNA línea para que TODO el grafo
cargue desde la API en vez del JSON embebido") se hizo de forma **parcial y
seguridad-primero**: el Grafo Temporal (`engine/temporal-graph.js`) ahora
consulta `/api/ontology/status` y muestra un badge "◈ ontología: N objetos"
cuando está configurada (verificación cruzada visible), pero **NO reemplaza**
`window.NODE_BY_ID`/`window.LINKS` como fuente de datos — de esos dependen
directamente 7 pestañas más (mapa, mercado, análisis, geopolítica,
simulación, Second Brain, Canvas) en un archivo de 12,568 líneas. Reemplazar
la fuente de datos central el mismo día de una reunión de inversión, sin
poder hacer regresión completa de cada pestaña, era un riesgo desproporcionado
frente al beneficio inmediato. **Recomendación:** hacer el swap completo en
una sesión dedicada, con checklist de regresión de las 8 pestañas, cuando no
haya una demo en vivo horas después.

## Fases 2-5

No iniciadas. Ver roadmap. Con la ontología ya en pie (Fase 1), la Fase 2
(Acciones: `CrearTesis`, `AnotarObjeto`, `RegistrarDecision`…) puede
apoyarse directamente en `apply_event()` — el mecanismo de escritura
auditada ya existe, solo falta el catálogo con validación por tipo y la UI.

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
