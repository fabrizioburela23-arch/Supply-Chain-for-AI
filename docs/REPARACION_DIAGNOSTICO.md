# Misión de reparación — Diagnóstico (2026-10-04)

Entregable de la regla 1 ("primero diagnóstico, después código"). **No se tocó
código.** Todo lo que sigue se reprodujo contra producción con las herramientas
MCP de Khipus (solo lectura) y leyendo el código del repo. Al final está el plan
y las decisiones que necesito de Fabrizio antes de empezar a corregir.

Leyenda: **CONFIRMADO** = se reprodujo tal como se describió · **DISTINTO** = el
síntoma es real pero la causa o el alcance no es el descrito · **NO CONFIRMADO**
= no pude reproducirlo como bug (y digo qué haría falta para cerrarlo).

---

## 0. Resumen en diez líneas

1. **Investigación (P0)**: confirmado. Un job con 2 de 4 agentes caídos se publica
   `done` y su síntesis no dice que faltan agentes. No hay cola, no hay reintentos,
   no hay "corta-circuito" cuando un proveedor no tiene saldo. El error "IA ocupada"
   que vimos lo produce **nuestro propio semáforo** (AI_MAX_CONCURRENCY=4) cuando
   varios jobs corren a la vez.
2. **Comité (P0)**: confirmado. Con fiabilidad 0.5 (= "sin historial") cada
   conclusión pesa igual que una validada; bastan 2 conclusiones para deliberar;
   los falsadores son texto libre y uno de ellos confirma la tesis; la evidencia
   "calculada por Khipus" entra como fuente externa (0.85).
3. **n_scored = 0**: hoy NO es un bug: el primer checkpoint vence el 5-oct y el
   primer "final" el 28-oct. Lo que sí está mal: la evaluación diaria solo corre
   si alguien abre el mapa.
4. **Grafo (P1)**: confirmado y con causa raíz: la base Postgres se migró el
   3-jul-2026 ANTES de que se corrigieran las direcciones de ~150 enlaces y antes
   de que existiera la tabla de alias → en la base hay entidades duplicadas
   (Luminar/Luminar_Lidar…) y enlaces al revés (Meta→TSMC "fab") que el catálogo
   ya no tiene. Procedencia vacía en TODOS los eventos de migración.
5. **Riesgo (P1)**: el backtest 13/250 es una tautología (umbral en muestra) —
   confirmado. Las correlaciones bajas **no** las pude confirmar como bug del
   motor: con series sintéticas el motor calcula bien, SPY/VOO dan 1.0 y las
   fechas de los peores días de Linde coinciden con sus resultados reales.
   El Sharpe "raro" es mezcla de retorno geométrico con Sharpe aritmético (rf=0),
   no una tasa libre de riesgo del 10 %.
6. **World Monitor (P2)**: las capas GDELT no están "pendientes": GDELT responde
   **HTTP 404**. La hora nula de "inestabilidad" es por diseño (valor curado
   actual), falta decir "curado, sin hora".
7. **Operación (P2)**: hay 60 tests del MCP con dobles, pero ningún chequeo contra
   el despliegue vivo ni un registro diario guardado.
8. Nada de esto requiere servicios nuevos ni más presupuesto.
9. Estimación: ~20 commits (uno por arreglo, cada uno con su test) — 2 a 3 días.
10. Necesito 7 decisiones (sección 5) y tu OK para empezar por P0.

---

## 1. Mapa del sistema (qué habla con qué)

```
Navegador (app.html + engine/*.js)                 IAs externas (Claude.ai, etc.)
   │  /api/*                                            │  POST /mcp  (tokens kmcp_, OAuth)
   ▼                                                    ▼
server.py (Flask, 1 worker × 12 hilos) ── blueprints ── mcp_server/ (22 herramientas, SOLO lectura
   │                                                      salvo preview/submit_order → cola humana)
   ├─ core/ai.py        cascada Claude→Gemini→NVIDIA, semáforo AI_MAX_CONCURRENCY=4,
   │                    guardián de cifras, gasto en core/ai_usage.py (tope USD 2/día research)
   ├─ core/quotes.py    precios en vivo (Yahoo → Finnhub → FMP…)  ← el agente de precios
   │                    está corrigiendo esto en paralelo (sin desplegar)
   ├─ core/risk_report.py  VaR/correlaciones (Yahoo 1 año) — lo usan PORT VAR, comité,
   │                    carteras y el MCP get_risk_report
   ├─ core/world.py     World Monitor: GDELT (3 capas) + USGS + EONET + curados
   ├─ research/         runner.py (jobs, 1 hilo por job), llm.py (cascada por agente),
   │                    context.py (evidencia), outcomes.py (checkpoints vs SPY),
   │                    committee.py (convicción → decisión → tamaño), debate.py
   ├─ ontology/         Postgres append-only: events → objects/links materializados
   └─ brokerage/        Alpaca por cliente; toda orden pasa por preview→confirm (PIN)

Estado persistente:  Postgres (ontología + research_* + broker_* + mcp_*)
Estado en memoria:   cachés (precios, world, risk _HIST_CACHE), semáforos, rate limits
Catálogo (código):   nodes/*.js → data/grafo_v0.json (949 nodos / 2.526 links)

Trabajos "programados" (no hay cron real):
  · live_caps.refresh  ← lo dispara /api/market/live_caps cuando alguien abre el mapa
      └─ 1×/día: research/outcomes.evaluate_due (califica predicciones vencidas)
      └─ RESEARCH_AUTO_EVENTS (apagado): investigación por anomalías/resultados
  · World Monitor: refresco por capa al pedirla (stale-while-revalidate), sin precalentar
  · Research jobs: hilo por job, sin cola
```

Dos verdades del grafo (NO fusionadas): el catálogo del repo (correcto y actual) y
la base Postgres (migrada 3-jul-2026 + expansión multicapa 2-ago-2026 + ~216
objetos que el repo no puede reconstruir). No existe chequeo de consistencia.

---

## 2. Reproducción de cada hallazgo

### P0-A · Pipeline de investigación

| # | Hallazgo | Estado | Evidencia (producción, 4-oct 17:0x UTC) | Causa raíz |
|---|---|---|---|---|
| A1 | Jobs incompletos publicados como `done` | **CONFIRMADO** | TSMC job `2ac4552d…`: status `done`; fundamental ✓ supply_chain ✓, **news ✗ technical ✗** ("IA ocupada" en claude, gemini y nvidia). Síntesis: 6 positivas / 1 riesgo, sin avisar que faltan 2 de 4 agentes. Alphabet `d6874bf1…`: `done` con technical ✗ (Anthropic sin saldo → Gemini 503 → NVIDIA ocupado). | `research/runner.py:431` — `job.status = 'done' if ok or not job.agents else 'failed'`: basta UN agente. La síntesis (`synthesize`, runner.py ~330-365) no lleva cobertura. `get_research` muestra `last_job.status` sin la lista de agentes caídos. |
| A2 | Sin cola ni límite de concurrencia | **CONFIRMADO** | Mismo job TSMC: los 3 proveedores dicen "ocupado" a la vez — eso es nuestro semáforo, no los proveedores. | `execute_job_async` (runner.py:440-460) = un hilo demonio por job, sin tope. `RESEARCH_PARALLEL=3` solo limita agentes DENTRO de un job. El único freno es `core/ai.py:72` ("AI busy: too many concurrent requests", semáforo de 4) → el comité + chat + 2 jobs ya lo saturan. |
| A3 | Sin reintentos con backoff para 429/503/busy | **CONFIRMADO** | Alphabet technical: Gemini 503 una sola vez y pasa al siguiente. | `research/llm.py:189-205` `RoutedProvider.structured_generate`: un intento por proveedor, sin espera. `core/ai.py` reintenta UNA vez tras 1 s (`CLAUDE_RETRY_SLEEP_S`) — insuficiente para un 503 o un "busy". |
| A4 | Sin corta-circuito cuando un proveedor no tiene saldo | **CONFIRMADO** | Cada agente de cada job vuelve a probar Anthropic y recibe el error de saldo antes de pasar a Gemini (visible en `errors` de los runs de Alphabet). | `research/llm.py:96-99` `available()` solo mira si la clave existe. No hay estado "caído hasta las HH:MM". |
| A5 | Presupuesto agotado → agente `skipped`, no se encola para mañana | **CONFIRMADO** (por código; hoy no estaba agotado) | — | `runner.py:137-142`: run `skipped` con "presupuesto diario agotado" y el job igual termina `done`. |
| A6 | Falta endpoint de salud del pipeline | **DISTINTO** | `/api/health` existe (server.py:906) pero solo dice qué claves hay. `/api/research/budget` y `/activity` existen. | No hay un lugar que diga: cola, proveedores caídos, última evaluación de outcomes, capas del mundo. |

### P0-B · Comité y validación de conclusiones

| # | Hallazgo | Estado | Evidencia | Causa raíz |
|---|---|---|---|---|
| B1 | `n_scored = 0`, el comité trabaja sin validación | **DISTINTO** (hoy no es bug; sí hay un defecto de operación) | `get_track_record`: `agents: []`, 0 filas. Claims más antiguas: 28-sep-2026. Checkpoints: SHORT 7 d (interino) / 30 d (final); MEDIUM 30/90/180; LONG 90/180/365. 28-sep + 7 = **5-oct** → nada vence todavía; primer "final" el 28-oct. | `research/outcomes.py:55-61`. Y la evaluación diaria (`core/live_caps.py:66`) solo corre cuando alguien abre el mapa y la caché está vencida — depende del tráfico de la UI, no del servidor. Los checkpoints de 5/20/60 días hábiles que pides no existen (decisión D3). |
| B2 | Fiabilidad 0.5 en todo y sin etiqueta "no validado"; tamaño sin tope | **CONFIRMADO** | Memo Nvidia `2122eac6…`: 9 claims, `reliability 0.5` en las 9, `track_record n=0` en los 4 agentes, decisión BUY, peso objetivo **5,30 %** (= 2 % / vol 37,7 %), sin ninguna marca de "no validado". | `research/committee.py:97` `w = cal * (rel / PRIOR_REL)` → con 0.5 el peso es la confianza completa. `compute_sizing` solo aplica el tope del mandato (10 %). |
| B3 | Delibera sin cobertura mínima | **CONFIRMADO** | TSMC: con 2 de 4 agentes el comité deliberaría igual (MIN_CLAIMS=2 y las 2 conclusiones existen). | `committee.py:66` `MIN_CLAIMS = 2` es la única puerta; no mira qué agentes hablaron. |
| B4 | Falsadores de texto libre; uno confirma la tesis; nunca se marca `falsified` | **CONFIRMADO** | Memo Nvidia, falsador 1: "El precio supera con claridad y volumen el máximo de 236.54 USD **o** inicia una corrección de más del 10 %". Romper el máximo CONFIRMA una compra. Viene copiado de la claim técnica (neutral), donde sí tenía sentido. | `committee.py:417` `falsifiers_es: List[str]` (texto). No hay {métrica, operador, umbral, fecha} ni chequeo diario; ninguna claim puede pasar a `falsified`. |
| B5 | Evidencia autorreferencial `khipus:ratios:*` como fuente | **CONFIRMADO** | Claim de Alphabet con UNA sola evidencia de tipo `analysis` ("Ratios financieros calculados por Khipus"), fiabilidad 0.85, confianza 0.6. | `research/context.py:345` y `:359` → `add('analysis', …)`. No existe `computed` ni tope de confianza para cifras de dinero sin fuente primaria externa. |
| B6 | Memo vencido sigue "propuesto" | **CONFIRMADO** (menor) | Memo Nvidia `expired: true` (TTL 72 h), status `proposed`. El corretaje ya rechaza órdenes con memo vencido (fix 2026-10-04). | Solo falta mostrarlo como "vencido" en UI/MCP. |

### P1-C · Grafo y ontología

| # | Hallazgo | Estado | Evidencia | Causa raíz |
|---|---|---|---|---|
| C1 | Procedencia vacía | **CONFIRMADO** | `get_ontology_object` TSMC (198 enlaces), Luminar, Luminar_Lidar: `provenance: []`; todos los eventos `source_id: null` (canales `migration_v0`, `migration_v0_links`, `expansion_multicapa`). | La migración y la expansión multicapa no crearon objetos Source; `properties.source` es un texto suelto. |
| C2 | `valid_from` 2000-01-01 de relleno | **CONFIRMADO** (diseño documentado) | TSMC: todos los enlaces del catálogo con `2000-01-01`. | `scripts/migrate_v0_to_ontology.py:59` `GENESIS`. Honesto en el código, pero en UI/MCP se lee como fecha real. |
| C3a | Entidades duplicadas | **CONFIRMADO** | En Postgres existen **Luminar y Luminar_Lidar**, **Mobileye y Mobileye_Auto**, **Butterfly y ButterflyNetwork** como objetos distintos con propiedades distintas (margen −0.5 vs −1.2, capex ~$0.2B vs ~$100M). El catálogo ya los fusiona (`nodes/nodes_seed.js:2527-2530`, NODE_ID_ALIAS). | La base se migró el 3-jul-2026, antes de la tabla de alias (que "antes NO se exportaba"). |
| C3b | Enlaces duplicados | **CONFIRMADO** | Postgres: TSMC→Nvidia `fab` ×2 (+ `supply` ×1), TSMC→AMD ×2, TSMC→Apple ×2 (pesos 6 y 5). Catálogo: **48 pares** con más de un enlace (Nvidia→CoreWeave ×3, Broadcom→Alphabet ×2…). | Dos catálogos fuente (seed + expand) sin deduplicar en la migración; en el catálogo el merge no colapsa pares. |
| C4 | Direcciones sospechosas | **CONFIRMADO, con causa** | Postgres: `Meta→TSMC fab`, `Tesla→TSMC fab`, `Qwen→TSMC fab`, `Luminar_Lidar→TSMC supply`, `Mobileye_Auto→TSMC supply` (al revés). Catálogo actual: `TSMC→Meta fab` "Fabrica sus ASICs MTIA" (correcto). | `nodes/links_expand.js:6-8`: "CANONIZADO (Etapa 2, 2026-07): source PROVEE a target" — la corrección de direcciones de ~150 enlaces se hizo **después** de migrar la base (3-jul). La base nunca se corrigió (y no se puede re-migrar: destructivo). |
| C5 | Relaciones que no son suministro aparecen como "proveedores" | **DISTINTO** | Equinix `top_suppliers` incluye Colliers, Fitch, Carlyle, C&W tipo `partner`. | `mcp_server/tools.py:381-386` `_edges` devuelve TODAS las aristas entrantes; la herramienta las llama "suppliers" pero sí expone `type`. Es un problema de etiqueta/filtro, no de datos. |
| C6 | Enlaces "no verificados" con peso | **CONFIRMADO** | `FedEx→TSMC` w=1 "contrato específico no verificado públicamente"; `Cathay_Cargo→TSMC` w=2 "no verificada con fuente pública". Pesan en NRS y matrices como los verificados. | No existe campo `verified`. |
| C7 | Taxonomía mezclada | **CONFIRMADO** | En la misma columna `rel_type`: supply/fab/partner/cloud/invest/license/owns/ppa/deploy (catálogo) + usa/fabrica/domina/depende/compite (hechos ONT_*) + affects (factores). 303 enlaces del catálogo con `rel` vacío. | Nunca se definió un vocabulario cerrado. |
| C8 | Cifras del catálogo sin `as_of` | **DISTINTO** | 526 nodos con `margin`, 311 con `capex_2026`, **0** con fecha propia. Equinix: margen op. 0.17 (catálogo) vs 27,02 % (en vivo), lado a lado sin fecha. El bloque del MCP sí lleva `as_of` = fecha de exportación del snapshot, no de la cifra. | Las cifras se escribieron a mano en nodes/*.js sin fecha. |
| C9 | Falta Analog Devices (ADI) | **CONFIRMADO** | Ningún nodo con `mkt: ADI` ni "Analog" en los 949. | — |
| C10 | Dos fuentes de verdad sin chequeo | **CONFIRMADO** | Catálogo 949/2.526 vs Postgres 1.294 objetos (~216 no reconstruibles); difieren en direcciones, duplicados e ids. | No existe script de consistencia. |

### P1-D · Motor de riesgo

| # | Hallazgo | Estado | Evidencia | Causa raíz |
|---|---|---|---|---|
| D1 | `backtest95` siempre 13/250 | **CONFIRMADO** | SPY, VOO, LIN, AAPL, MSFT, NVDA+AMD, carteras de 4: **todos 13/250** (esperado 12,5). | `core/risk_report.py:164-165`: el umbral es el cuantil 5 % **de la misma muestra** → por construcción ~5 % de días lo superan. No mide nada. |
| D2 | Correlaciones sospechosamente bajas | **NO CONFIRMADO como bug del motor** | Pruebas con series sintéticas (sin red): ρ=0,6 conocida → el motor da 0,608; SPY vs SPY → 1,0; una serie desplazada 1 día → 0,014. Producción: SPY/VOO = 1,0; NVDA/AMD 0,46; LIN/APD 0,52 (plausibles). Peores días de LIN: 31-oct-2025, 5-feb-2026, 31-jul-2026 = fechas reales de resultados de Linde → las fechas están alineadas. Siguen raras: LIN–SPY 0,056, MSFT–ASML −0,02, AAPL 0,36. | No encontré defecto en `compute`. Desde este contenedor no puedo bajar precios de Yahoo (bloqueado) para contrastar con una fuente independiente. Para cerrarlo: test de alineación + verificación en tu PC (o en producción con un endpoint de diagnóstico). Si el dato es real, hay que decirlo en la UI; si Yahoo entrega series raras para algunos tickers, se verá ahí. |
| D3 | Sharpe inconsistente (implica rf≈10 %) | **DISTINTO** | EQIX: retorno 39,14 %, vol 25,23 %, Sharpe 1,31 — reproducido exactamente con **rf = 0** usando la media aritmética diaria. Cartera 1,78 ídem. | `risk_report.py:179-180`: `return_ann_pct` es geométrico ((1+μ)^252−1) y `sharpe` usa la media aritmética (μ/σ·√252). Comparar los dos "inventa" una rf. No se usa ^IRX (aunque `core/options.py:128` ya lo baja). |

### P2-E · World Monitor

| # | Hallazgo | Estado | Evidencia | Causa raíz |
|---|---|---|---|---|
| E1 | Capas GDELT "pendientes" | **DISTINTO** | 17:18 UTC: `pending` (primera consulta). 17:19 UTC: las 3 capas `error_code: http_404` — **GDELT responde 404**. USGS, EONET y curadas: OK. | `core/world.py:989-998` llama `api.gdeltproject.org/api/v2/geo/geo?mode=PointData&format=GeoJSON…`. Hay que contrastar con la documentación actual de GDELT GEO 2.0 (parámetros/ruta). No se puede probar desde este contenedor (bloqueado). Además no hay precalentado: cada deploy deja la caché fría. |
| E2 | Inestabilidad con `time = null` | **DISTINTO** (diseño) | `instability:*` y `chokepoints:*`: `time: null`, `source: "Khipu (curated)"`. | `world.py:1051-1068`: `time_kind: 'current'`, `fetched_at` real. Falta decir "curado, sin hora" + fecha de la curación (`static: true`). |

### P2-F · Operación

| # | Hallazgo | Estado | Evidencia |
|---|---|---|---|
| F1 | Falta smoke test del MCP en cada deploy | **DISTINTO** | `tests/test_mcp.py` tiene 60 tests (con dobles) y `test_server_smoke.py` 24. No hay prueba contra el despliegue VIVO ni se guarda un "último chequeo". |
| F2 | Logs no estructurados | **CONFIRMADO** | `log.warning('research job %s: %s', …)` texto suelto; sin job_id/agente/proveedor/latencia como campos. |

### Lo que NO es bug (con evidencia)

- `n_scored = 0` hoy (nada vence hasta el 5-oct; primer final el 28-oct).
- Hora nula en capas curadas (es un valor actual, no un evento).
- Memo vencido a los 3 días (TTL configurable; el corretaje ya lo bloquea).
- El Sharpe: la aritmética es correcta con rf=0; el problema es de etiqueta.
- El número 13/250 es "correcto" para un backtest en muestra; el método es el inútil.

---

## 3. Plan priorizado (un commit por arreglo, test que falla antes y pasa después)

Formato: **commit — qué — test**. Nada crea servicios ni gasto nuevo. Los contratos
del MCP solo ganan campos.

### P0 · Investigación (5 commits)

1. **Estado honesto `partial`** — `job.status`: `done` solo si TODOS los agentes
   terminaron; `partial` si falta alguno; `coverage {ok, failed, skipped, missing}`
   en el job, en la síntesis (`note` bilingüe "faltan X de 4 agentes") y en
   `get_research` / `get_research_job` (campos nuevos). El dedupe no reutiliza un
   `partial` para la misma petición. — test: job con 1 agente caído → `partial` + cobertura.
2. **Cola de jobs** — cola FIFO con `RESEARCH_JOB_CONCURRENCY` (default 1; el comité
   y el chat conservan el cupo interactivo). Los jobs esperan `queued` en vez de
   chocar con el semáforo de IA. — test: 3 jobs → 1 corre, 2 esperan, orden FIFO.
3. **Reintentos + corta-circuito** — en `RoutedProvider`: hasta 3 intentos por
   proveedor con backoff exponencial + jitter (2→20 s) SOLO para 429/503/529/busy/
   timeout; corta-circuito por proveedor (sin saldo/clave inválida → "caído" 30 min,
   se salta limpio y se registra). — test: proveedor con 503 dos veces y luego OK →
   1 resultado, 2 esperas; proveedor "sin saldo" → no se vuelve a llamar.
4. **Reintentar solo lo que falta** — `run_research` acepta `only_missing: true`
   (campo opcional; mismo nombre de herramienta) y el botón "↻ completar" en la UI;
   presupuesto agotado → el job queda `queued` con `resume_at = mañana` en vez de
   `skipped`. — test: job `partial` + only_missing → corre solo news/technical.
5. **Salud del pipeline** — `GET /api/research/health` (cola, proveedores caídos,
   gasto del día, última evaluación de outcomes) + bloque `research` en
   `/api/health`. — test: respuesta con los campos.

### P0 · Comité (5 commits)

6. **"No validado" + tope de tamaño** — `validated: false` y etiqueta bilingüe en el
   memo cuando el agente tiene `n_scored < min_n`; mientras tanto el peso objetivo se
   limita al **50 %** (decisión D1). — test: track record vacío → tamaño = mitad.
7. **Cobertura mínima** — sin `fundamental` + 3 de 4 agentes → decisión
   `INSUFFICIENT_DATA` (HOLD con motivo, sin sala de debate) (decisión D2). — test.
8. **Falsadores estructurados + chequeo diario** — `{metric, op, threshold,
   deadline}` generados por el agente y validados contra la postura (un BUY no puede
   tener "el precio rompe el máximo" como falsador; se descarta y se registra); chequeo
   diario con precios reales → claim `falsified` + memo marcado. Los textos actuales
   se conservan. — test con `price_fn` falso.
9. **Evidencia calculada = `computed`** — `khipus:ratios:*` pasa a `source_type:
   'computed'` (valor nuevo; filas viejas se quedan) con fiabilidad 0.6; una claim con
   cifras de dinero sin fuente primaria externa queda con confianza tope 0.5 y
   etiqueta. — test.
10. **Outcomes sin depender de la UI + checkpoints 5/20/60 hábiles** — hilo diario
    del servidor (arranque + cada 24 h) y checkpoints nuevos en días hábiles
    (decisión D3), append-only (etiquetas nuevas, las viejas siguen). — test con
    `price_fn` falso: claim a 5 días → fila `hit/miss`.

### P1 · Grafo y ontología (4 commits + lista de revisión)

11. **Auditoría automática** — `scripts/audit_graph.py`: duplicados (entidades y
    pares), direcciones catálogo vs base, procedencia vacía, fechas de relleno, pesos
    sin verificar, taxonomía, cifras sin fecha, empresas faltantes propuestas (ADI…).
    Reporte JSON + Markdown; corre en `pytest` (no falla, informa) y 1×/día en el
    servidor (`/api/ontology/audit/last`). — test sobre el snapshot.
12. **Fusión de duplicados por eventos** — evento nuevo `ObjectMerged`
    (Luminar_Lidar→Luminar, Mobileye_Auto→Mobileye, ButterflyNetwork→Butterfly):
    enlaces re-apuntados con `LinkRetracted` + `LinkCreated` (source
    `repair:merge`), el id viejo queda como alias. **Backup antes** (`pg_dump` del
    esquema de ontología) y script de rollback = retractar los eventos `repair:*`.
    — test en base local.
13. **Corrección de direcciones** — el script compara base vs catálogo y produce la
    **lista de enlaces al revés para tu revisión** (regla 6). Con tu OK se aplican
    como `LinkRetracted` + `LinkCreated` (source `repair:direction`). — test.
14. **Taxonomía, `verified` y fechas** — vista de clase de relación
    (supply/fab/customer/invest/ppa/partner/coverage/competitor) sin reescribir
    `rel_type`; campo `verified` (false si el texto dice "no verificado"; esos pesos
    no cuentan en NRS/matrices); `get_supply_chain` separa `partners` de
    `top_suppliers` y añade `relation_class`/`verified` (solo campos nuevos); cifras del
    catálogo con `as_of: "catálogo jul-2026"` explícito y etiqueta "no es dato en vivo".
    — tests.

### P1 · Motor de riesgo (3 commits)

15. **Tests sintéticos + alineación** — series con ρ conocida, desfase de 1 día,
    auto-correlación; el reporte añade `aligned_days` por símbolo y avisa si una
    serie perdió >5 % de fechas frente al índice. — test (los que corrí hoy, fijados).
16. **Backtest fuera de muestra + Kupiec** — VaR rodante (ventana 120 d, estimado con
    el pasado, contado en el día siguiente) + test de Kupiec (p-valor); el 13/250 se
    conserva etiquetado "en muestra (referencia)". — test con serie sintética.
17. **Sharpe con ^IRX** — rf del T-bill a 3 meses (helper compartido con
    `core/options.py`), `return_ann_arith_pct` y `return_ann_geom_pct` separados y
    explicados en el "?". — test.

### P2 · World Monitor (2 commits)

18. **GDELT 404** — contrastar ruta/parámetros con la documentación vigente (no puedo
    desde aquí; lo verifico con los logs de Railway o desde tu PC). Si GDELT cambió a
    algo con clave o pago → **fuera de alcance**: la capa queda apagada con mensaje
    honesto, sin proveedor nuevo. — test con respuesta grabada.
19. **Precalentado + capas curadas honestas** — al arrancar se calientan las capas
    (sin bloquear); `static: true` + `curated_as_of` en inestabilidad/estrechos. — test.

### P2 · Operación (2 commits)

20. **Smoke test del despliegue vivo** — `scripts/smoke_mcp.py` (herramientas de
    lectura con un token `kmcp_` de scope read; sin órdenes) + chequeo diario guardado
    en tabla `ops_checks` y `GET /api/ops/last_check`. Si GitHub Actions está
    disponible sin costo, corre tras cada push a `main`. — test.
21. **Logs estructurados** — `LOG_JSON=on`: líneas JSON con job_id/agente/proveedor/
    latencia/costo; sin cambiar los mensajes actuales. — test.

Cada commit actualiza `REPAIR_LOG.md` (problema, causa, cambio, cómo verificarlo) y
`docs/ESTADO.md`. Despliegue: tras cada prioridad (P0 investigación, P0 comité, …),
con resumen corto para ti.

---

## 4. Trabajo en curso que no es de la misión

- **Agente de precios** (Finnhub/FMP en vivo, pedido antes de la misión): tiene
  cambios **sin commitear** en `app.html`, `server.py`, `core/quotes.py`,
  `core/providers/market.py`, `core/live_caps.py` + `tests/test_quotes_live.py`.
  Es reparación (datos en vivo que no llegaban), pero **no lo despliego sin tu OK**:
  cuando termine te paso el resumen y lo revisamos aparte.
- Pausado hasta que termine la misión: Canvas estilo Power BI, estética profesional,
  tensores de la ontología (son features; la misión dice "no agregar").

---

## 5. Decisiones que necesito de ti (con mi recomendación)

| # | Decisión | Recomendación |
|---|---|---|
| D1 | `min_n` para considerar un agente "validado" y tope mientras no lo esté | **5 aciertos/fallos calificados** (ya es MIN_N) y **50 %** del peso objetivo |
| D2 | Regla de cobertura del comité | **`fundamental` + 3 de 4 agentes**; si no → `INSUFFICIENT_DATA` |
| D3 | Checkpoints en días hábiles | SHORT: 5 y 20 (final 20) · MEDIUM: 20, 60 y 180 (final 180) · LONG: 60, 180 y 365 (final 365) · INTRADAY: 1. Los actuales siguen hasta vencer. |
| D4 | Fuente de verdad | **Postgres** es la verdad de la ontología (como dice CLAUDE.md); el catálogo es la semilla. Las correcciones (direcciones, fusiones) se hacen en la base por eventos y el chequeo diario reporta diferencias. |
| D5 | Direcciones al revés | Te paso la lista (≈150 enlaces del lote `links_expand`) y **no aplico nada hasta tu OK**. |
| D6 | Proveedores de IA este mes (sin saldo en Anthropic) | Cambiar en Railway, sin código: `AI_ORDER=gemini,claude,nvidia` y `RESEARCH_MODEL_DEFAULT=gemini,claude:deep,nvidia`. Cuando repongas saldo, volver. |
| D7 | GDELT | Si resulta que ahora pide clave/pago: dejar las 3 capas apagadas con aviso honesto (sin proveedor nuevo). |

---

## 6. Qué hacer ahora

1. Lee la sección 0 y la 5. Responde las 7 decisiones (puedes decir "todo como
   recomiendas").
2. Dame el **OK para empezar por P0 · Investigación** (commits 1-5).
3. Si quieres, cambia ya en Railway las dos variables de D6 (no cuesta nada y evita
   que cada agente pierda tiempo con Anthropic sin saldo).
