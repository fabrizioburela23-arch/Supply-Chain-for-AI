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

## Fase 2 — ACCIONES: WRITE-BACK AUDITADO

**Estado: ✅ COMPLETA**

- [x] `ontology/actions.py`: catálogo de 9 Acciones con validación Pydantic
      (equivalente a Zod del roadmap): `CrearTesis`, `AnotarObjeto`,
      `MarcarRiesgo`, `ProponerVinculo`, `ConfirmarVinculo`, `RechazarVinculo`,
      `RegistrarDecision`, `AjustarPosicion`, `CorregirDato`.
- [x] Cada Acción ejecuta su efecto de dominio con eventos normales
      (`ObjectCreated`/`Updated`, `LinkCreated`) Y deja siempre un evento
      `ActionExecuted` — el rastro auditable (`actor` obligatorio: "toda
      Acción queda atribuida a alguien").
- [x] `execute_action()`: punto de entrada único, valida con el esquema del
      catálogo y rechaza actor vacío u objeto inexistente antes de escribir
      nada (rollback automático vía `session_scope`).
- [x] API: `POST /api/ontology/actions/<tipo>` (body: `{actor, ...campos}`),
      `GET /api/ontology/actions?actor=&type=&object_id=` (para el Registro).
- [x] Tests: `tests/test_ontology_actions.py` (10 tests: creación de tesis +
      vínculo automático, rechazo de stance/actor inválidos, objeto
      inexistente, `MarcarRiesgo` actualiza propiedades, propuesta→confirmación
      de vínculo, propuesta→rechazo cierra el intervalo de validez, decisión +
      ajuste de posición vinculados, corrección de dato con antes/después
      auditado, registro filtrable y ordenado). 36/36 tests totales del repo.
- [x] **UI real** (no solo backend):
      - Botón **"＋ Acción"** en la ficha de objeto del Grafo Temporal
        (`engine/temporal-graph.js`): formulario compacto según el tipo de
        objeto (empresas: crear tesis / marcar riesgo / registrar decisión /
        anotar; objetos de ontología: solo anotar). Pide el nombre del autor
        una vez (se recuerda en `localStorage`) — sin sistema de login, fuera
        de alcance de esta fase.
      - Panel **"📋 Registro"** (overlay global, mismo patrón que 🩺
        diagnóstico): timeline de todas las Acciones ejecutadas, filtrable
        por autor, con ícono/etiqueta por tipo y el detalle (razón/rationale).
      - Debajo de cada ficha de objeto: mini-registro de las últimas acciones
        sobre ESE objeto específico.
- [x] **Validado con un caso real**: se usó `CorregirDato` para arreglar el
      dato de SpaceX (`preipo: true → false`) que motivó gran parte de esta
      sesión — con auditoría de quién lo corrigió y por qué, en vez de un
      edit manual silencioso en el código fuente.

## Fase 3 — AGENTES QUE PROPONEN, HUMANO QUE APRUEBA

**Estado: ✅ COMPLETA**

- [x] `ontology/agents.py`: contrato `observe(session)->signals` /
      `propose(session, signal)->dict|None`. 4 agentes v1 (no 5 — Cronista se
      implementó como reporte de solo-lectura, ver abajo, no como agente que
      propone Acciones):
      - **Centinela NRS**: recalcula riesgo (fórmula geo+grado+margen+
        concentración, réplica server-side de `computeNRS`) y propone
        `MarcarRiesgo` si cruza el umbral (70).
      - **Lector GDELT**: muestrea las 5 empresas más conectadas, busca
        noticias reales vía GDELT, propone `AnotarObjeto` con resumen (IA).
      - **Guardián de Cartera**: deriva holdings de `PositionAdjustment`
        (Fase 2) — **limitación honesta documentada**: el portafolio
        "real" del usuario vive en `localStorage`, este agente solo ve
        posiciones registradas EN la ontología vía la Acción
        `AjustarPosicion`.
      - **Cartógrafo**: detecta empresas sin ningún vínculo vigente
        (nodos aislados), propone `AnotarObjeto` señalando la brecha.
- [x] Runtime: **sin scheduler interno** (gunicorn 2 workers duplicaría cada
      corrida) — `POST /api/ontology/agents/run` bajo demanda (botón manual
      o cron externo), con deduplicación por agente+tipo+objeto+ventana de
      tiempo para no repetir la misma propuesta en cada corrida.
- [x] Cola de aprobación: `ProposedAction` (pending/approved/rejected).
      `GET /api/ontology/agents/proposals`, `POST .../approve` (ejecuta la
      Acción real, actor='<agente> → aprobado por <humano>'),
      `POST .../reject`. Doble-aprobación bloqueada (409).
- [x] **Cronista** (Brief Matinal): `GET /api/ontology/agents/brief` —
      resumen en lenguaje natural de acciones + propuestas + nuevos
      vínculos en las últimas N horas. Informativo, sin cola de aprobación.
- [x] UI: botón **"🔔 Propuestas"** (overlay) — lista, permite EDITAR los
      campos antes de aprobar (inputs editables en cada card), Aprobar/
      Rechazar, botón "🔍 Revisar ahora" dispara `agents/run`.
- [x] Tests: `tests/test_ontology_agents.py` (7 tests) — Centinela detecta
      riesgo alto, Cartógrafo detecta aislamiento, dedupe entre corridas,
      aprobar ejecuta la Acción, rechazar no ejecuta nada, brief matinal,
      endpoints Flask.
- [x] Bug encontrado y corregido en el camino: la fórmula NRS (heredada del
      cliente, `app.html:computeNRS`) no tiene límite inferior en el término
      de margen — empresas pre-revenue con márgenes muy negativos (ej.
      Rigetti -2.5) inflaban el score muy por encima de 100 antes de
      truncar. En la réplica server-side SÍ se acotó `[0,20]`; **el cliente
      original conserva el mismo comportamiento sin corregir** — se dejó así
      a propósito (no se tocó una fórmula que el usuario ve en producción
      sin que lo pida), queda anotado aquí como candidato a revisar.

## Fase 4 — LENGUAJE DE COMANDOS + MOTOR DE ALERTAS

**Estado: ✅ COMPLETA**

- [x] `engine/khipu_lang.js`: parser de `<ENTIDAD> <FUNCIÓN> [ARGS]`.
      Se intenta ANTES de llamar a la IA en `command_center.js` (Bixby) — si
      no calza con la gramática, `tryParse()` devuelve `null` y Bixby sigue
      su flujo normal de lenguaje natural. Comandos exactos no gastan tokens
      ni tiempo de red a Claude.
      - `<TICKER> DES/GP/SUP/CLI/RISK/NEWS/SIM/FA/THESIS [texto]` — cada uno
        despacha a funcionalidad YA CONSTRUIDA (Second Brain, mapa,
        `__tkgOpenObj` del Grafo Temporal, `activateStress`,
        `/api/fundamentals`, o crea una tesis vía `/api/ontology/actions/CrearTesis`).
      - `PORT VAR` / `PORT PL` — usa `/api/portfolio-risk` y las posiciones
        de `MKT.pos` (localStorage) + cotizaciones cacheadas.
      - `GRAPH ASOF <fecha>` / `GRAPH DIFF <Nd>` — mueve la línea de tiempo
        del Grafo Temporal (nuevo hook `window.__tkgSetDate`) o consulta
        `/api/ontology/graph/diff`.
      - `ALERT <TICKER> PX|NRS > <valor>` / `ALERT REGION <región> NEWS` /
        `ALERT LIST` — crea/lista alertas en la ontología.
      - Resolución de entidad case-insensitive por id o por ticker (`.mkt`).
- [x] Motor de alertas: modelo `Alert` (Postgres) + `ontology.agents.
      evaluate_alert()`/`check_alerts()` — soporta `price` (Finnhub, reusa
      `server._fetch_quote_raw`, extraído de la ruta `/api/quote/<ticker>`
      con el mismo cambio ya cubierto por los smoke tests existentes),
      `nrs` (override o calculado), `news_region` (anotaciones recientes
      que mencionan la región). CRUD: `POST/GET/DELETE /api/ontology/alerts`,
      evaluación bajo demanda: `GET /api/ontology/alerts/check`.
- [x] Cliente: `OntologyAlerts` (en `app.html`) sondea cada 2 min (si el
      usuario activó notificaciones en Preferencias) y dispara
      `Notification` del navegador — **deduplicado por sesión** (una alerta
      no vuelve a notificar mientras la pestaña siga abierta, para no
      spamear si la condición sigue vigente). Coexiste con el `PriceAlerts`
      preexistente (cliente, solo-precio, solo-localStorage) sin
      reemplazarlo — resuelven necesidades distintas.
- [x] Tests: `tests/test_ontology_alerts.py` (5 tests) — dispara con NRS
      alto, no dispara bajo el umbral, no truena sin `FINNHUB_KEY`, CRUD +
      evaluación completa vía API, rechaza métrica inválida.
- [x] Verificado en Node (sin DOM) el parser completo: reconoce comandos
      válidos, devuelve `null` para lenguaje natural (sin falsos positivos
      con frases como "comprar 10 NVDA"), maneja bien la ausencia de
      `__tkgSetDate`/red sin romper.

## Fase 5

No iniciada. Ver roadmap — buena parte de sus entregables (precios en vivo,
fundamentales, diagnóstico de pipelines) ya existían antes de esta sesión de
ontología; falta específicamente el linaje visible (tooltip ⓘ fuente/
antigüedad) y extender 🩺 con staleness. El "dato alternativo nuevo" (fabs o
CelesTrak↔contratos) el roadmap mismo lo marca como sesión aparte al final.

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
