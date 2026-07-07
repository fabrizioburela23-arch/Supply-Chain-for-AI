# ESTADO — Khipus AI Finance Intelligence · Ontología (Palantir-style)

Archivo vivo. Cada sesión de trabajo en la ontología lee esto primero y lo
actualiza al terminar. Ver `ROADMAP_KHIPUS_ONTOLOGIA.md` (adjuntado por el
usuario) para el plan completo por fases, y `docs/AUDITORIA.md` para las
correcciones de arquitectura respecto al roadmap original (backend real =
Flask/Python, no Node; `/v1/*` ya es la API pública monetizada; Neo4j Aura ya
está conectado).

---

# REDISEÑO MAYOR 2026-07 — mapa único con capas + motor de matrices

Decisiones de Fabrizio (2026-07-03, no reabrir sin razón nueva): UN solo mapa
con capas activables; app final de 4 pestañas (MAPA/MERCADO/INSIGHTS/GUÍA) con
Bixby/terminal flotante; motor de predicción INTERNO (adiós MiroFish) centrado
en insights de inversión; matrices numéricas por tipo de relación moduladas
por hiperaristas (todo bitemporal en la ontología); 40 categorías → ~9
macro-sectores sin perder detalle; SOLO Railway (se elimina el modo
standalone); frecuencia de actualización configurable con automático APAGADO
por defecto; gasto de IA moderado; despliegue por etapas siempre verde;
limpieza agresiva de código muerto.

Auditoría multi-agente completa del repo hecha el 2026-07-03 (9 lectores):
hallazgos clave — 7 renderers de mapa independientes; 4 propagaciones de shock
inconsistentes; 31 empresas duplicadas; direcciones de arista opuestas
(546 vs 577); 67% de pesos w en default; ~700+ líneas visuales muertas;
rag/ y litellm/ nunca desplegados; hypergraph.js con node_impacts siempre
vacío (el slot del motor nuevo); contrato MiroFish a replicar =
{node_impacts, cascade_nodes, price_trajectories, report, chat, progress_pct}.

## Etapa 0 — Seguridad y cimientos: ✅ CÓDIGO COMPLETO (2026-07-03)

- [x] /api/trade/* (11 rutas) protegidas con PIN (X-Trade-Pin == env
      TRADE_PIN); sin TRADE_PIN el trading queda deshabilitado. El panel de
      trading pide el PIN una vez (localStorage.khipu_trade_pin). ANTES:
      cualquiera con la URL podía operar la cuenta Alpaca real.
- [x] /v1/auth/key: tiers de pago exigen X-Admin-Secret (KHIPU_ADMIN_SECRET).
- [x] Auto-trader: daily_pnl_pct real (equity vs last_equity de Alpaca) →
      el circuit-breaker diario ya puede saltar; stop-loss por posición
      implementado (cierra posiciones bajo el umbral). Antes: decorativos.
- [x] gunicorn 2 workers → 1 worker + 8 threads (el estado en memoria vivía
      duplicado y divergía por worker).
- [x] Ontología, 2 bugs de replay corregidos: RechazarVinculo ahora emite
      LinkRemoved (antes mutaba tablas sin evento → time-travel mostraba
      vínculos rechazados como vigentes); _links_active_at casa remociones
      comodín (sin rel_type) y respeta re-creaciones. +3 tests de regresión
      (isomorfismo replay==tablas). **51/51 tests contra Postgres real.**
- [x] sw.js SHELL sincronizado (faltaban 3 nodes/* y 4 vendor) + bump v28.
- [ ] PENDIENTE (paso manual de Fabrizio): variable TRADE_PIN en Railway
      (y KHIPU_ADMIN_SECRET si va a emitir claves de pago).
- Diferido a Etapa 1: extraer _ai_complete/_fetch_quote_raw a core/ (rompe
  la dependencia circular ontology→server).

## Etapa 1 — Limpieza masiva: ✅ COMPLETA (2026-07-05, 4 batches publicados)

- [x] Batch 1 (a2b09ff, −2,200 ln): rag/ + litellm/ + redis compose +
      nodes_core.js + PriceAlerts no-op + cadena Aladdin muerta + _mfChatSend
      + _drawWorldMap + _activateHypergraph roto + botón 🕸 + timeline
      duplicado + initSpaceOrbitCanvas + métodos muertos de graph3d +
      hypergraph save/load + 9 rutas Flask sin caller + paleta .dark
      duplicada + docs stale → docs/archive/.
- [x] Batch 2 (c24e85b): paquete core/ (config/http/ai/quotes) — server.py y
      ontology/agents.py importan de ahí; dependencia circular
      ontology→server ROTA (prerrequisito del motor de matrices).
- [x] Batch 3 (41beb40, −281 ln): modo standalone ELIMINADO — SERVER_MODE
      constante true, DataLayer solo-server, fuera todas las llamadas
      directas del navegador a Finnhub/FMP/Anthropic/Marketstack y el UI de
      keys (⚙ solo preferencias + salud). voice.js y secondbrain.js migrados
      al proxy. Smoke test real en navegador local: arranque limpio.
- [x] Batch 4: /v1/risk/portfolio y /api/portfolio-risk comparten
      _portfolio_risk_impl (antes duplicado verbatim de ~60 ln, contrato /v1
      intacto); _fetch_quote_raw(timeout=) reutilizado en los 3 loops batch;
      CLAUDE.md y este archivo actualizados.
- ⏸️ Diferido A PROPÓSITO a Etapa 4: consolidar los 3 pipelines de quotes del
  cliente (fetchQuotes/LivePrices/initLiveData) y los 2 sistemas de alertas
  vivos — el store único del mapa unificado los subsume; consolidarlos dos
  veces sería trabajo tirado.

## Etapa 2 — Datos limpios: ✅ COMPLETA (2026-07-06, 5 batches publicados)

**El grafo canónico ahora es: 407 empresas · 1,028 links · 9 tipos de
relación · 9 macro-sectores · dirección ÚNICA (source PROVEE a target).**

- [x] Batch 1 (e73be4f): ~2,550 líneas de datos inline salen de app.html →
      nodes/nodes_seed.js (extracción determinista, isomorfa 463/1163).
      Hechos temporales concat-safe (el orden de <script> ya no pierde datos).
- [x] Batch 2a (0df080b): RESOLUCIÓN DE ENTIDADES — 56 ids duplicados
      fusionados (463→407). NODE_ID_ALIAS = tabla canónica; el merge absorbe
      campos, redirige links, y NODE_BY_ID[alias] → nodo canónico (ids viejos
      siguen resolviendo). Dedupe (s,t,type). NO fusionados (ticker≠entidad):
      HashiCorp≠IBM, Qwen≠AlibabaCloud, Aerojet⊂L3Harris, Altium⊂Renesas.
- [x] Batch 2b (f9a4282): DIRECCIÓN ÚNICA — 1,168 filas reescritas
      físicamente, 425 volteadas, 66 re-tipadas (customer→supply,
      investor→invest → 9 tipos). Adjudicación arista por arista
      (clasificador de categorías+verbos en español + revisión manual de 375
      ambiguas + auditoría de 286 flips). 10/10 verdades de cadena en
      navegador; la cascada de TSMC ahora alcanza 112 empresas (incl. Nvidia
      y Apple — antes invisibles por direcciones opuestas).
- [x] Batch 3: MACRO-SECTORES — SECTORS9 + CAT_TO_SECTOR (40 cats → 9
      sectores con los colores NEXUS) en nodes_seed.js; 5 países faltantes
      añadidos a COUNTRIES (Israel/Australia/Europa/India/Canadá) + typo
      Japan→Japon; pase de pesos por señal textual (7×w6 monopolios,
      10×w5 principales, 5×w1 pilotos).
- [x] Batch 3 (cont.): MERGE ÚNICO — nodes/merge_graph.js
      (buildKhipusGraph) usado por app.html Y por el exportador; el
      export_graph_v0.js por rangos de línea hardcodeados fue reemplazado.
      data/grafo_v0.json regenerado canónico (407/1028/9 sectores) y
      migración a Postgres validada end-to-end (439 objetos, 0 ids sin
      resolver, 85 hechos fechados). 51/51 tests.
- ⏸️ Los pesos siguen siendo un prior débil (mayoría w=2): la re-derivación
  profunda (dependency-share por fundamentals) queda para la ingesta (12k) y
  el motor de matrices, que los recalculará con datos vivos.

## Etapa 3 — Motor de matrices + hiperaristas: ✅ NÚCLEO COMPLETO (2026-07-07)

Paquete **matrix/** (opcional y defensivo, como ontology/ — sin DATABASE_URL
responde 503 y la app sigue). Importa de core/ y de la ontología; NO toca
server.py salvo el registro del blueprint.

- [x] `matrix/engine.py`:
  - `build_matrices(session, as_of=)`: una matriz N×N por rel_type (9 tipos)
    desde los links VIGENTES o, con `as_of`, reconstruidos por VALIDEZ desde
    events (time-travel real, reusa `_links_active_at`). A[i,j] = i PROVEE a j
    (convención canónica Etapa 2); partner reflejado simétrico.
  - `active_factors()`: HIPERARISTAS = objetos type='Factor' + links 'affects'
    (weight = coeficiente). Cero cambio de esquema — reusa ObjectCreated/
    LinkCreated, así heredan bitemporalidad, auditoría y time-travel.
  - `fragility()` + `propagate()`: UN kernel de propagación de shocks
    (reemplaza las 4 implementaciones BFS divergentes del cliente).
    Modelo económico: transmisión normalizada POR TIPO de relación (un
    proveedor ÚNICO en su tipo transmite ~todo el shock; ser 1 de N pega
    poco), combinada por criticidad (fab≈supply > invest); impacto = máximo
    por ruta (no suma). Las hiperaristas aumentan la FRAGILIDAD del afectado
    (se aplica tras normalizar — por eso no se cancela).
  - `compute_metrics()`: grado in/out ponderado + tamaño de cascada +
    ranking de chokepoints por nodo.
- [x] `matrix/api.py` (blueprint /api/matrix/*): `/status`, `/<rel_type>`,
  `POST /impact {shock, magnitude, damping, max_hops, rel_weights, as_of}`,
  `/metrics`. Registrado defensivo en server.py.
- [x] Tests `tests/test_matrix.py` (5): verdades de cadena en las matrices,
  propagación TSMC→clientes con hops, hiperarista amplifica + time-travel la
  desactiva, chokepoints, endpoints HTTP. **56/56 tests totales.**
- [x] Validado end-to-end contra Postgres real: los chokepoints detectados
  son los reales de la industria — TSMC(265), PDF_Solutions, ARM, Amazon,
  Broadcom, Synopsys. El NRS server-side (computeNRS réplica) sigue en
  ontology/agents.py; la unificación NRS↔matriz (computed_metrics servido)
  se hará al conectar el frontend (Etapa 4/5).
- ⏸️ Diferido: tabla cache `matrix_snapshots` con watermark (hoy se computa
  on-demand; N≈440 → <30ms por matriz, no urge). Agente MatrixSentinel →
  ProposedAction cuando un chokepoint cruza umbral: se cablea en Etapa 5
  junto con el resto de auto-insights.

## Etapas siguientes (plan en las tareas de la sesión)
2. **Etapa 2 — Datos limpios**: resolución de entidades (31 duplicados),
   dirección única de aristas, taxonomía tipada, pesos re-derivados (LLM
   batch), datos fuera del monolito → JSON servido, swap frontend a la API.
3. **Etapa 3 — Motor de matrices + hiperaristas**: blueprint matrix/ (NumPy,
   sparse por rel_type, snapshots con watermark, computed_metrics para NRS
   servido), hiperaristas como Factor+affects (cero cambio de esquema),
   UN kernel de propagación, agente MatrixSentinel → ProposedAction.
4. **Etapa 4 — Mapa unificado con capas**: 7 renderers → 2 motores
   (grafo 2D + globo), LayerRegistry, 4 pestañas, 9 macro-sectores, un solo
   store de estado, borrar stack 3D conservando datos, regenerar Guía+Bixby.
5. **Etapa 5 — Predicciones internas + INSIGHTS**: kernel de matrices +
   presets como hiperaristas nombradas, War-Room como visualización,
   pestaña INSIGHTS (feed + brief + panel junto al mapa), control único de
   frecuencia (manual por defecto).

Entorno de desarrollo local (Windows, PC de Fabrizio, instalado 2026-07-03):
Python 3.11 (winget) + PostgreSQL 16 (winget, postgres/devpass, DB
khipus_test). Correr tests completos:
`DATABASE_URL=postgresql://postgres:devpass@localhost:5432/khipus_test pytest tests/ -q`

---

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

## Fase 5 — PROFUNDIDAD DE DATO + LINAJE

**Estado: ✅ COMPLETA (alcance recortado a propósito, ver nota)**

Buena parte de los entregables de esta fase (precios en vivo, fundamentales
FMP, diagnóstico de pipelines) ya existían antes de esta sesión de
ontología — no se reconstruyeron. Lo que sí se añadió:

- [x] Ficha de objeto (Grafo Temporal): linaje visible con ⓘ —
      precio: "Finnhub/FMP · hace Ns/min/h"; NRS: "calculado (fórmula)" o,
      si se fijó vía la Acción `MarcarRiesgo`, "fijado manualmente por
      <quién> — <razón>" (consulta aparte a `/api/ontology/objects/<id>`,
      no bloquea el render inicial de la ficha).
- [x] 🩺 diagnóstico → "Ontología": ahora incluye el evento más reciente
      (fecha + fuente) — primera señal de "qué tan fresca" está la ontología.
- ⏸️ **Diferido a propósito**: el "dato alternativo nuevo" (calendario de
  capex/fabs, o cruce CelesTrak↔contratos de lanzamiento) — el roadmap
  mismo lo marca como "sesión aparte al final", no parte de la secuencia
  principal. WebSocket de precios en tiempo real tampoco se implementó
  (la infraestructura de polling ya existente cubre la necesidad sin
  añadir una pieza de infraestructura nueva el mismo día).

## Roadmap completo: Fases 0-5 implementadas (con las notas de alcance de
## arriba). Ver también la sección "Fase 3" para el detalle del framework de
## agentes y "Fase 4" para el lenguaje KHIPU + alertas.

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
